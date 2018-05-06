from __future__ import unicode_literals

from calendar import timegm
from json import loads, dumps
from logging import getLogger
from logging import INFO

import transaction
from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from arche.events import ObjectUpdatedEvent
from pyramid.decorator import reify
from pyramid.interfaces import IRequest
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from zope.component import adapter
from zope.component.event import objectEventNotify
from zope.interface import implementer
from zope.interface import Interface
from six import string_types

from arche import logger
from arche.interfaces import ILocalRoles
from arche.interfaces import IRolesCommitLogger
from arche.interfaces import IRole
from arche.interfaces import IRoles
from arche.compat import IterableUserDict
from arche.compat import UserString


@implementer(IRole)
class Role(UserString):
    """ Base class for global / local roles. """
    title = ""
    description = ""
    inheritable = False
    assignable = False

    @property
    def principal(self):
        return self.data

    def __init__(self, principal, title = None, description = "", inheritable = False, assignable = False, required = ()):
        super(Role, self).__init__(principal)
        if title is None:
            title = principal
        self.title = title
        self.description = description
        self.inheritable = inheritable
        self.assignable = assignable
        try:
            if issubclass(required, Interface):
                required = (required,)
        except TypeError:
            pass # issubclass for a list will raise TypeError
        for iface in required:
            assert issubclass(iface, Interface)
        self.required = set(required)


@adapter(ILocalRoles)
@implementer(IRoles)
class Roles(IterableUserDict):

    def __init__(self, context):
        self.context = context
        #FIXME: Don't write OOBTrees unless they're needed!
        #Change it on setitem instead
        try:
            self.data = self.context.__local_roles__
        except AttributeError:
            self.context.__local_roles__ = OOBTree()
            self.data = self.context.__local_roles__

    def __setitem__(self, key, value):
        if value:
            value = self._adjust_to_set(value)
            self._check_roles(value)
            try:
                current = self.data[key]
            except KeyError:
                self._maybe_log(key, value, ())
                self.data[key] = OOSet(value)
                return
            # Check difference
            if set(current) != value:
                self._maybe_log(key, value, current)
                current.clear()
                current.update(value)
        elif key in self:
            del self[key]

    def __delitem__(self, key):
        self._maybe_log(key, (), self.data[key])
        del self.data[key]

    def __getitem__(self, key):
        return frozenset(self.data[key])

    def _adjust_to_set(self, value):
        if IRole.providedBy(value):
            value = set([value])
        elif isinstance(value, string_types):
            value = set([value])
        else:
            value = set(value)
        return value

    def _check_roles(self, roles):
        #Warn if it doesn't exist
        reg = get_current_registry()
        roles_principals = reg.roles.keys()
        for role in roles:
            if role not in roles_principals:
                logger.warn("The role %r doesn't exist. Permissions assigned at %r might not work" % (role, self.context))

    def add(self, key, value, event=True):
        value = self._adjust_to_set(value)
        current = set()
        if key in self:
            current.update(self[key])
        roles = value | current
        self[key] = roles
        if event:
            self.send_event()

    def remove(self, key, value, event=True):
        value = self._adjust_to_set(value)
        current = set()
        if key in self:
            current.update(self[key])
        roles = current - value
        if roles:
            self[key] = roles
        elif key in self:
            del self[key]
        if event:
            self.send_event()

    def set_from_appstruct(self, value, event=False):
        marker = object()
        removed_principals = set()
        [removed_principals.add(x) for x in self if x not in value]
        [self.pop(x) for x in removed_principals if x in self]
        for (k, v) in value.items():
            if self.get(k, marker) != v:
                self[k] = v
        if event:
            self.send_event()

    def get_any_local_with(self, role):
        assert isinstance(role, string_types) or IRole.providedBy(role)
        for (name, local_roles) in self.items():
            if role in local_roles:
                yield name

    def get_assignable(self, registry = None):
        if registry is None:
            registry = get_current_registry()
        roles = getattr(registry, 'roles', None)
        if roles == None: #pragma: no coverage
            logger.warning("No roles registered")
            roles = {}
        results = {}
        for role in registry.roles.values():
            if role.assignable != True:
                continue
            if role.required:
                for required in role.required:
                    if required.providedBy(self.context):
                        results[role.principal] = role
                        break
            else:
                results[role.principal] = role
        return results

    def __repr__(self): #pragma: no coverage
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s object at %#x>' % (classname, id(self))

    def send_event(self):
        event_obj = ObjectUpdatedEvent(self.context, changed=['local_roles'])
        objectEventNotify(event_obj)

    def _maybe_log(self, key, new, old):
        if not getattr(self.context, 'uid', None):
            return
        request = get_current_request()
        if not request.registry.settings.get('arche.log_roles', True):
            return
        rcl = IRolesCommitLogger(request, None)
        if rcl is None:
            # Skip in case adapter was unregistered
            return
        rcl.add(self.context.uid, key, new, old)


@implementer(IRolesCommitLogger)
@adapter(IRequest)
class RolesCommitLogger(object):
    __doc__ = IRolesCommitLogger.__doc__
    logger = None
    loglvl = INFO # <- Integer!

    def __init__(self, request):
        self.request = request
        if self.logger is None:
            self.logger = getLogger('arche_jsonlog.security.roles')

    @classmethod
    def set_logger(cls, logger):
        if isinstance(logger, string_types):
            logger = getLogger(logger)
        cls.logger = logger

    @reify
    def entries(self):
        try:
            return self.request._roles_commit_logger
        except AttributeError:
            self.request._roles_commit_logger = {}
            return self.request._roles_commit_logger

    @property
    def attached(self):
        """ Did we add the commit hook? """
        # Using the add method will cause this attribute to be created since it interacts with entries
        return hasattr(self.request, '_roles_commit_logger')

    def add(self, uid, key, new, old):
        if not self.attached:
            txn = transaction.get()
            txn.addAfterCommitHook(self.commit_hook)
        uid_entries = self.entries.setdefault(uid, {})
        key_entries = uid_entries.setdefault(key, {})
        # Only set old state the first time
        key_entries.setdefault('old', frozenset(old))
        # Set the last version of the new state
        key_entries['new'] = frozenset(new)

    def prepare(self):
        output = {'contexts': {}}
        contexts = output['contexts']
        for (uid, context_entries) in self.entries.items():
            for (key, entry) in context_entries.items():
                added = entry['new'] - entry['old']
                removed = entry['old'] - entry['new']
                # There's no simple way to make roles json encodable, despite the fact that
                # they're user strings. Hence the conversion.
                if added or removed:
                    if uid not in contexts:
                        contexts[uid] = {}
                    contexts[uid][key] = ke = {}
                if added:
                    ke['+'] = [str(x) for x in added]
                if removed:
                    ke['-'] = [str(x) for x in removed]
        if not contexts:
            # Clean up
            del output['contexts']
        if output:
            output.update(
                userid=self.request.authenticated_userid,
                time=timegm(self.request.dt_handler.utcnow().timetuple()),
                url=self.request.url,
            )
        return output

    def format(self, payload):
        return dumps(payload)

    def log(self, payload):
        self.logger.log(self.loglvl, payload)

    def commit_hook(self, status, *args, **kwargs):
        """ The commit hook passed to the transaction.
            Note that any exceptions caused here will be swallowed by
            the transaction system and never shown!
        """
        if status:
            payload = self.prepare()
            if payload:
                payload = self.format(payload)
                self.log(payload)


def register_roles(config, *roles):
    reg = config.registry
    if not hasattr(reg, 'roles'):
        reg.roles = {}
    for role in roles:
        assert IRole.providedBy(role), "Must be a role object"
        if role in reg.roles: #pragma : no coverage
            logger.warning("Overriding role %r" % role)
        reg.roles[role.principal] = role


def includeme(config):
    config.registry.registerAdapter(Roles)
    config.add_directive('register_roles', register_roles)
    # Hook logging here
    log_roles_name = config.registry.settings.get('arche.log_roles', '')
    if log_roles_name:
        RolesCommitLogger.set_logger(log_roles_name)
        config.registry.registerAdapter(RolesCommitLogger)
