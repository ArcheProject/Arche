from __future__ import unicode_literals
from UserString import UserString
from UserDict import IterableUserDict

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from pyramid.threadlocal import get_current_registry
from zope.component import adapter
from zope.interface import implementer

from arche import _
from arche.interfaces import IContent
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

    def __init__(self, principal, title = None, description = "", inheritable = False, assignable = False):
        super(Role, self).__init__(principal)
        if title is None:
            title = principal
        self.title = title
        self.description = description
        self.inheritable = inheritable
        self.assignable = assignable
        


# class RolesRegistry(object):
#     """ Manages available roles. """
#     
#     def __init__(self):
#         self.data = set()
# 
#     def add(self, role):
#         assert IRole.providedBy(role)
#         self.data.add(role)
# 
#     #set-isch API
#     def remove(self, role): self.data.remove(role)
#     def __contains__(self, item): return item in self.data
#     def __len__(self): return len(self.data)
#     def __iter__(self): return iter(self.data)
# 
#     def inheritable(self):
#         return [x for x in self if x.inheritable == True]
# 
#     def assignable(self):
#         return [x for x in self if x.assignable == True]


@adapter(IContent)
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
            #Make sure it exist
            roles_principals = get_current_registry().acl.get_roles()
            if IRole.providedBy(value):
                value = [value]
            for role in value:
                assert role in roles_principals, "'%s' isn't a registered role. Context: %r" % (role, self.context)
            self.data[key] = OOSet(value)
        elif key in self.data:
            del self.data[key]

    def set_from_appstruct(self, value):
        marker = object()
        removed_principals = set()
        [removed_principals.add(x) for x in self if x not in value]
        [self.pop(x) for x in removed_principals if x in self]
        for (k, v) in value.items():
            if self.get(k, marker) != v:
                self[k] = v

def includeme(config):
    config.registry.registerAdapter(Roles)