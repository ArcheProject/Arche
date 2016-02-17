from __future__ import unicode_literals
from UserString import UserString
from UserDict import IterableUserDict

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from pyramid.threadlocal import get_current_registry
from zope.component import adapter
from zope.interface import implementer
from zope.interface import Interface
from six import string_types

from arche import logger
from arche.interfaces import ILocalRoles
from arche.interfaces import IRole
from arche.interfaces import IRoles


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
            self.data[key] = OOSet(value)
        elif key in self.data:
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

    def add(self, key, value):
        value = self._adjust_to_set(value)
        current = set()
        if key in self:
            current.update(self[key])
        roles = value | current
        self[key] = roles

    def remove(self, key, value):
        value = self._adjust_to_set(value)
        current = set()
        if key in self:
            current.update(self[key])
        roles = current - value
        if roles:
            self[key] = roles
        elif key in self:
            del self[key]

    def set_from_appstruct(self, value):
        marker = object()
        removed_principals = set()
        [removed_principals.add(x) for x in self if x not in value]
        [self.pop(x) for x in removed_principals if x in self]
        for (k, v) in value.items():
            if self.get(k, marker) != v:
                self[k] = v

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
