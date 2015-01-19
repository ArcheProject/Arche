from contextlib import contextmanager
from hashlib import sha512

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

from arche import _
from arche.interfaces import IRoles
from arche.models.roles import Role


PERM_VIEW = 'perm:View'
PERM_EDIT = 'perm:Edit'
PERM_REGISTER = 'perm:Register'
PERM_DELETE = 'perm:Delete'
PERM_MANAGE_SYSTEM = 'perm:Manage system'
PERM_MANAGE_USERS = 'perm:Manage users'
PERM_REVIEW_CONTENT = 'perm:Review content'



ROLE_ADMIN = Role('role:Administrator',
                  title = _(u"Administrator"),
                  description = _(u"Default 'superuser' role."),
                  inheritable = True,
                  assignable = True,)
ROLE_EDITOR = Role('role:Editor',
                  title = _(u"Editor"),
                  description = _(u"Someone who has normal edit permissions."),
                  inheritable = True,
                  assignable = True,)
ROLE_VIEWER = Role('role:Viewer',
                  title = _(u"Viewer"),
                  description = _(u"Someone who's allowed to view."),
                  inheritable = True,
                  assignable = True,)
ROLE_OWNER = Role('role:Owner',
                  title = _(u"Owner"),
                  description = _(u"Special role for the initial creator."),
                  inheritable = False,
                  assignable = False,)
ROLE_REVIEWER = Role('role:Reviewer',
                  title = _(u"Reviewer"),
                  description = _(u"Review and publish content. Usable when combined with a workflow that implements review before publish."),
                  inheritable = True,
                  assignable = True,)
ROLE_EVERYONE = Role(Everyone,
                  title = _("Everyone"),
                  description = _("Including anonymous"),
                  assignable = False)
ROLE_AUTHENTICATED = Role(Authenticated,
                  title = _("Authenticated users"),
                  assignable = False)


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
    inherited_roles = request.registry.acl.get_roles(inheritable = True)
    if not name.startswith('group:'):
        root = find_root(context)
        groups = root['groups'].get_users_group_principals(name)
        result.update(groups)
        #Fetch any local roles for group
        for group in groups:
            result.update(groupfinder(group, request))
    initial_context = context
    while context:
        try:
            if context == initial_context:
                result.update([x for x in context.local_roles.get(name, ())])
            else:
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
        return registry.acl
    except AttributeError:
        raise ACLException("ACL not initialized, include arche.security")

def get_local_roles(context, registry = None):
    if registry is None:
        registry = get_current_registry()
    return registry.getAdapter(context, IRoles)

def get_roles_registry(registry = None):
    #Deprecated wrapper
    if registry is None:
        registry = get_current_registry()
    return registry.acl.get_roles()

def sha512_hash_method(value, hashed = None):
    return sha512(value).hexdigest()

def bcrypt_hash_method(value, hashed = None):
    #Package seems broken right now.
    import bcrypt

    if hashed is None:
        hashed = bcrypt.gensalt()
    try:
        return bcrypt.hashpw(value.encode('utf-8'), hashed)
    except ValueError: #Invalid salt
        return bcrypt.hashpw(value.encode('utf-8'), bcrypt.gensalt())

def includeme(config):
    """ Initialize ACL and populate with default acl lists.
    """
    #ACL registry must be created first
    config.include('arche.models.acl')
    config.include('arche.models.roles')
    aclreg = config.registry.acl
    from arche.models.acl import ACLEntry

    class _InheritACL(ACLEntry):
        def add(self, role, perms): pass
        def remove(self, role, perms): pass
        def __call__(self): raise AttributeError()

    aclreg['inherit'] = _InheritACL(title = _("Inherit"),
                                    description = _("Fetch the ACL from the parent object"))        
    aclreg['default'] = 'inherit'
    private = aclreg.new_acl('private', title = _("Private"))
    private.add(ROLE_ADMIN, ALL_PERMISSIONS)
    private.add(ROLE_OWNER, [PERM_VIEW, PERM_EDIT, PERM_DELETE])
    private.add(ROLE_EDITOR, [PERM_VIEW, PERM_EDIT, PERM_DELETE])
    private.add(ROLE_VIEWER, [PERM_VIEW])
    private.add(ROLE_REVIEWER, [PERM_REVIEW_CONTENT]) #May not be able to view
    
    public = aclreg.new_acl('public', title = _("Public"))
    public.add(ROLE_ADMIN, ALL_PERMISSIONS)
    public.add(Everyone, [PERM_VIEW])
    public.add(ROLE_REVIEWER, [PERM_REVIEW_CONTENT])
    
    review = aclreg.new_acl('review', title = _("Review"))
    review.add(ROLE_ADMIN, ALL_PERMISSIONS)
    review.add(ROLE_OWNER, [PERM_VIEW])
    review.add(ROLE_EDITOR, [PERM_VIEW])
    review.add(ROLE_VIEWER, [PERM_VIEW])
    review.add(ROLE_REVIEWER, [PERM_VIEW, PERM_REVIEW_CONTENT])
    