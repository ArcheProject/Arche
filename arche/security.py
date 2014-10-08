from UserDict import IterableUserDict
from UserString import UserString
from contextlib import contextmanager

from BTrees.OOBTree import OOBTree
from BTrees.OOBTree import OOSet
from pyramid.security import (NO_PERMISSION_REQUIRED,
                              Everyone,
                              Authenticated,
                              Allow,
                              Deny,
                              Allowed,
                              DENY_ALL,
                              ALL_PERMISSIONS,
                              AllPermissionsList)
from pyramid.threadlocal import get_current_registry
from pyramid.traversal import find_root
from pyramid.interfaces import IAuthenticationPolicy
from pyramid.interfaces import IAuthorizationPolicy
from zope.component import adapter
from zope.interface import implementer

from arche import _
from arche.interfaces import IContent
from arche.interfaces import IRole
from arche.interfaces import IRoles


PERM_VIEW = 'perm:View'
PERM_EDIT = 'perm:Edit'
PERM_REGISTER = 'perm:Register'
PERM_DELETE = 'perm:Delete'
PERM_MANAGE_SYSTEM = 'perm:Manage system'
PERM_MANAGE_USERS = 'perm:Manage users'


class ACLException(Exception):
    """ When ACL isn't registered, or something else goes wrong. """

@contextmanager
def authz_context(context, request):
    before = request.environ.pop('authz_context', None)
    request.environ['authz_context'] = context
    try:
        yield
    finally:
        del request.environ['authz_context']
        if before is not None:
            request.environ['authz_context'] = before


def has_permission(request, permission, context=None):
    """ The default has_permission does care about the context,
        but it calls the callback (in our case 'groupfinder') without the correct
        context. This methods hacks in the correct context. Keep it here until
        this has been fixed in Pyramid."""
    if context is None:
        context = request.context
    reg = request.registry
    authn_policy = reg.queryUtility(IAuthenticationPolicy)
    if authn_policy is None:
        return Allowed('No authentication policy in use.')
    authz_policy = reg.queryUtility(IAuthorizationPolicy)
    if authz_policy is None:
        raise ValueError('Authentication policy registered without '
                         'authorization policy') # should never happen
    with authz_context(context, request):
        principals = authn_policy.effective_principals(request)
        return authz_policy.permits(context, principals, permission)


def groupfinder(name, request):
    """ This method is called on each request to determine which
        principals a user has.
        Principals are groups, roles, userid and perhaps Authenticated or similar.
        
        This method also calls itself to fetch any local roles for groups.
    """
    if name is None: #Abort for unauthenticated - no reason to use CPU
        return ()
    result = set()
    context = request.environ.get(
        'authz_context', getattr(request, 'context', None))
    if not context:
        return ()
    inherited_roles = get_roles_registry(request.registry).inheritable()
    if not name.startswith('group:'):
        root = find_root(context)
        groups = root['groups'].get_users_group_principals(name)
        result.update(groups)
        #Fetch any local roles for group
        for group in groups:
            result.update(groupfinder(group, request))
    while context:
        try:
            result.update([x for x in context.local_roles.get(name, ()) if x in inherited_roles])
        except AttributeError:
            pass
        context = context.__parent__
    return result

def get_acl_registry(registry = None):
    """ Get ACL registry"""
    if registry is None:
        registry = get_current_registry()
    try:
        return registry._acl
    except AttributeError:
        raise ACLException("ACL not initialized, include arche.security")


class ACLEntry(IterableUserDict):
    """ Contains ACL information.
        Behaves like a callable dict.
    """
    def __init__(self):
        self.data = {}

    def add(self, role, perms):
        #Check what kind of role?
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
        if isinstance(current, AllPermissionsList):
            raise ValueError("Permission list for '%s' currently set to Pyramids all permissions object. "
                             "It doesn't support clearing some permissions. ")
        [current.remove(x) for x in perms if x in current]

    def __call__(self):
        items = [(Allow, role, perms) for (role, perms) in self.items()]
        items.append(DENY_ALL)
        return items


class ACLRegistry(IterableUserDict):
    """ Manages available ACL. """
    def __init__(self):
        self.data = {}
        self.default = ACLEntry()

    def __setitem__(self, key, aclentry):
        assert isinstance(aclentry, ACLEntry)
        self.data[key] = aclentry

    def get_acl(self, acl_name):
        try:
            return self[acl_name]()
        except KeyError:
            return self.default()


def get_roles_registry(registry = None):
    """ Get roles registry"""
    if registry is None:
        registry = get_current_registry()
    return registry._roles


@implementer(IRole)
class Role(UserString):
    """ Base class for global / local roles. """
    title = u""
    description = u""
    inheritable = False
    assign_local = False
    assign_global = False

    @property
    def principal(self):
        return self.data

    def __init__(self, principal, **kwargs):
        if not principal.startswith('role:'):
            raise ValueError("Roles must always start with ':role'")
        super(Role, self).__init__(principal)
        for (key, value) in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError("This class doesn't have any '%s' attribute." % key)
            setattr(self, key, value)

ROLE_ADMIN = Role('role:Administrator',
                  title = _(u"Administrator"),
                  description = _(u"Default 'superuser' role."),
                  inheritable = True,
                  assign_local = True,
                  assign_global = True,)
ROLE_EDITOR = Role('role:Editor',
                  title = _(u"Editor"),
                  description = _(u"Someone who has normal edit permissions."),
                  inheritable = True,
                  assign_local = True,
                  assign_global = True,)
ROLE_VIEWER = Role('role:Viewer',
                  title = _(u"Viewer"),
                  description = _(u"Someone who's allowed to view."),
                  inheritable = True,
                  assign_local = True,
                  assign_global = True,)
ROLE_OWNER = Role('role:Owner',
                  title = _(u"Owner"),
                  description = _(u"Special role for the initial creator."),
                  inheritable = False,
                  assign_local = True,
                  assign_global = False,)


class RolesRegistry(object):
    """ Manages available roles. """
    
    def __init__(self):
        self.data = set()

    def add(self, role):
        assert IRole.providedBy(role)
        self.data.add(role)

    #set-isch API
    def remove(self, role): self.data.remove(role)
    def __contains__(self, item): return item in self.data
    def __len__(self): return len(self.data)
    def __iter__(self): return iter(self.data)

    def inheritable(self):
        return [x for x in self if x.inheritable == True]

    def assign_local(self):
        return [x for x in self if x.assign_local == True]

    def assign_global(self):
        return [x for x in self if x.assign_global == True]


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
            roles_principals = get_roles_registry()
            for role in value:
                assert role in roles_principals, "'%s' isn't a role" % role
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

def get_local_roles(context, registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.queryAdapter(context, IRoles)


def includeme(config):
    from arche.utils import get_content_factories

    config.registry._roles = rr = RolesRegistry()
    rr.add(ROLE_ADMIN)
    rr.add(ROLE_EDITOR)
    rr.add(ROLE_VIEWER)
    rr.add(ROLE_OWNER)
    config.registry.registerAdapter(Roles)
    config.registry._acl = aclreg =  ACLRegistry()
    aclreg.default.add(ROLE_ADMIN, ALL_PERMISSIONS)
    aclreg.default.add(ROLE_EDITOR, [PERM_VIEW, PERM_EDIT, PERM_DELETE])
    aclreg.default.add(ROLE_VIEWER, [PERM_VIEW])
    aclreg.default.add(Everyone, [PERM_VIEW])
    #Default add perms - perhaps configurable somewhere else?
    #Anyway, factories need to be included first otherwise this won't work!
    factories = get_content_factories(config.registry)
    add_perms = []
    for factory in factories.values():
        if hasattr(factory, 'add_permission'):
            add_perms.append(factory.add_permission)
    aclreg.default.add(ROLE_ADMIN, add_perms)
