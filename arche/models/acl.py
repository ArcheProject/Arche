from __future__ import unicode_literals
from UserDict import IterableUserDict

from pyramid.security import AllPermissionsList
from pyramid.security import Allow
from pyramid.security import DENY_ALL
from pyramid.threadlocal import get_current_registry
from zope.interface import implementer
import six

from arche import _
from arche import logger
from arche.interfaces import IACLRegistry
from arche.interfaces import IRole
from arche.models.roles import Role


class ACLEntry(IterableUserDict):
    """ Contains ACL information.
        Behaves like a callable dict.
    """
    title = ""
    description = ""

    def __init__(self, title = "", description = ""):
        self.data = {}
        self.title = title
        self.description = description

    def add(self, role, perms):
        if not IRole.providedBy(role):
            reg = get_current_registry()
            roles = getattr(reg, 'roles', {})
            try:
                role = roles[role]
            except KeyError:
                logger.info("Creating a role object from %r" % role)
                role = Role(role)
        if isinstance(perms, six.string_types):
            perms = (perms,)
        if isinstance(perms, AllPermissionsList):
            self[role] = perms
        else:
            current = self.setdefault(role, set())
            if not isinstance(current, AllPermissionsList):
                current.update(perms)

    def remove(self, role, perms):
        if isinstance(perms, six.string_types):
            perms = (perms,)
        if isinstance(perms, AllPermissionsList):
            del self[role]
            return
        current = self.get(role, set())
        if isinstance(current, AllPermissionsList): #pragma : no coverage
            raise ValueError("Permission list for '%s' currently set to Pyramids all permissions object. "
                             "It doesn't support clearing some permissions. ")
        [current.remove(x) for x in perms if x in current]

    def __call__(self):
        items = [(Allow, role, perms) for (role, perms) in self.items()]
        items.append(DENY_ALL)
        return items

    def __repr__(self): #pragma: no coverage
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s object with %s roles at %#x>' % (classname,
                                                     len(self),
                                                     id(self))


@implementer(IACLRegistry)
class ACLRegistry(IterableUserDict):
    """ Manages available ACL. """
    def __init__(self):
        self.data = {}

    def __setitem__(self, key, aclentry):
        if isinstance(aclentry, ACLEntry):
            self.data[key] = aclentry
            if not aclentry.title: #pragma : no coverage
                aclentry.title = key
        elif isinstance(aclentry, six.string_types):
            if aclentry not in self:
                raise ValueError("ACLRegistry can't link the name %r to %r since it doesn't exist." % (key, aclentry))
            self.data[key] = aclentry
        else:
            raise TypeError("Can only have ACLEntries or strings (links to other ACL Entries as value, got %r)" % aclentry)
        

    def get_acl(self, acl_name):
        acl = self.get(acl_name, None)
        if isinstance(acl, six.string_types):
            #Linked acl
            return self[acl]()
        try:
            return acl()
        except TypeError: #pragma: no coverage
            #Only when something is badly configured. Should only happen during testing
            return (DENY_ALL,)

    def is_linked(self, acl_name):
        return isinstance(self.get(acl_name, None), six.string_types)

    def __repr__(self): #pragma: no coverage
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s object at %#x>' % (classname, id(self))

    def new_acl(self, key, title = "", description = ""):
        assert key not in self, "%r already exists as an ACL Entry" % key
        self[key] = ACLEntry(title = title, description = description)
        return self[key]


class _InheritACL(ACLEntry):
    def add(self, role, perms): pass
    def remove(self, role, perms): pass
    def __call__(self): raise AttributeError()


def includeme(config):
    if not hasattr(config.registry, 'acl'):
        config.registry.acl = ACLRegistry()
    config.registry.acl['inherit'] = _InheritACL(title = _("Inherit"),
                                                 description = _("Fetch the ACL from the parent object"))
