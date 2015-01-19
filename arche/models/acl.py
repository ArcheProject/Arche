from __future__ import unicode_literals
from UserDict import IterableUserDict

from pyramid.security import AllPermissionsList
from pyramid.security import Allow
from pyramid.security import DENY_ALL
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
            logger.info("Creating a role object from %r" % role)
            role = Role(role)
        if isinstance(perms, basestring):
            perms = (perms,)
        if isinstance(perms, AllPermissionsList):
            self[role] = perms
        else:
            current = self.setdefault(role, set())
            if not isinstance(current, AllPermissionsList):
                current.update(perms)

    def remove(self, role, perms):
        if isinstance(perms, basestring):
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
            #Only when something is badly configured. Should only happen during testig
            return (DENY_ALL,)

    def get_roles(self, inheritable = None, assignable = None):
        results = set()
        for acl in self.values():
            if isinstance(acl, six.string_types):
                continue
            results.update([x for x in acl.keys() if IRole.providedBy(x)])
        
        if inheritable is not None:
            for role in tuple(results):
                if role.inheritable != inheritable:
                    results.remove(role)
        if assignable is not None:
            for role in tuple(results):
                if role.assignable != assignable:
                    results.remove(role)
        return results

    def is_linked(self, acl_name):
        return isinstance(self.get(acl_name, None), six.string_types)

    def __repr__(self): #pragma: no coverage
        klass = self.__class__
        classname = '%s.%s' % (klass.__module__, klass.__name__)
        return '<%s object at %#x>' % (classname, id(self))


def includeme(config):
    if not hasattr(config.registry, 'acl'):
        config.registry.acl = ACLRegistry()
