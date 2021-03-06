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
from arche import logger
from arche.interfaces import IRoles
from arche.models.roles import Role


PERM_VIEW = 'perm:View'
PERM_EDIT = 'perm:Edit'
PERM_REGISTER = 'perm:Register'
PERM_DELETE = 'perm:Delete'
PERM_MANAGE_SYSTEM = 'perm:Manage system'
PERM_MANAGE_USERS = 'perm:Manage users'
PERM_REVIEW_CONTENT = 'perm:Review content'
PERM_ACCESS_AUTH_SESSIONS = 'perm:Access auth sessions'


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
                  assignable = True,)
ROLE_REVIEWER = Role('role:Reviewer',
                  title = _(u"Reviewer"),
                  description = _("Review and publish content. Usable when combined "
                                  "with a workflow that implements review before publish."),
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
        this has been fixed in Pyramid.
    """
    return _has_permission(request, permission, context=context)


def principal_has_permisson(request, principal, permission, context=None):
    """ Check permissions for another principal. (For instance a userid)
    """
    return _has_permission(request, permission, context=context, principal=principal)


_marker = object()


def _has_permission(request, permission, context=None, principal=_marker):
    try:
        if context is None:
            context = request.context
    except AttributeError:
        #Special cases like exceptions and similar
        return DENY_ALL
    reg = request.registry
    authn_policy = reg.queryUtility(IAuthenticationPolicy)
    if authn_policy is None:
        return Allowed('No authentication policy in use.')
    authz_policy = reg.queryUtility(IAuthorizationPolicy)
    if authz_policy is None:
        raise ValueError('Authentication policy registered without '
                         'authorization policy') # should never happen
    with authz_context(context, request):
        if principal is _marker:
            principals = authn_policy.effective_principals(request)
        else:
            principals = groupfinder(principal, request)
        return authz_policy.permits(context, principals, permission)


def context_effective_principals(request, context = None):
    if context is None:
        context = request.context
    authn_policy = request.registry.queryUtility(IAuthenticationPolicy)
    if authn_policy is None:
        return [Everyone]
    with authz_context(context, request):
        return authn_policy.effective_principals(request)


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
    inherited_roles = get_roles(registry = request.registry, inheritable = True)
    if not name.startswith('group:'):
        try:
            root = find_root(context)
        except AttributeError:
            #For instance broken objects doesn't have __parent__
            root = None
        groups = ()
        #FIXME: We may want to add the groups to the catalog instead for easier lookup
        if root and 'groups' in root:
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
        try:
            context = context.__parent__
        except AttributeError:
            #For instance broken objects
            context = None
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
    #FIXME: Deprecated, remove this
    if registry is None:
        registry = get_current_registry()
    return registry.getAdapter(context, IRoles)


def get_roles(registry = None, **filterkw):
    if registry is None:
        registry = get_current_registry()
    results = {}
    roles = getattr(registry, 'roles', None)
    if roles == None:
        logger.warning("No roles registered")
        roles = {}
    for role in registry.roles.values():
        filtered = False
        for (k, v) in filterkw.items():
            if getattr(role, k) != v:
                filtered = True
                break
        if filtered == False:
            results[role.principal] = role
    return results


def sha512_hash_method(value, hashed = None):
    return sha512(value.encode('utf-8')).hexdigest()


def bcrypt_hash_method(value, hashed = None):
    #Package seems broken right now.
    import bcrypt

    if hashed is None:
        hashed = bcrypt.gensalt()
    try:
        return bcrypt.hashpw(value.encode('utf-8'), hashed)
    except ValueError: #Invalid salt
        return bcrypt.hashpw(value.encode('utf-8'), bcrypt.gensalt())


def auth_session_factory(settings):
    from pyramid.authentication import SessionAuthenticationPolicy
    return SessionAuthenticationPolicy(callback = groupfinder)


def auth_tkt_factory(settings):
    from pyramid.authentication import AuthTktAuthenticationPolicy

    def read_salt(settings):
        from uuid import uuid4
        from os.path import isfile
        filename = settings.get('arche.salt_file', None)
        if filename is None:
            print("\nUsing random salt which means that all users must reauthenticate on restart.")
            print("Please specify a salt file by adding the parameter:\n")
            print("arche.salt_file = <path to file>\n")
            print("in paster ini config and add the salt as the sole contents of the file.\n")
            return str(uuid4())
        if not isfile(filename):
            print("\nCan't find salt file specified in paster ini. Trying to create one...")
            f = open(filename, 'w')
            salt = str(uuid4())
            f.write(salt)
            f.close()
            print("Wrote new salt in: %s" % filename)
            return salt
        else:
            f = open(filename, 'r')
            salt = f.read()
            if not salt:
                raise ValueError("Salt file is empty - it needs to contain at least some text. File: %s" % filename)
            f.close()
            return salt

    return AuthTktAuthenticationPolicy(
        secret = read_salt(settings),
        callback = groupfinder,
        hashalg = 'sha512'
    )

def includeme(config):
    """ Enable security subsystem.
        Initialize ACL and populate with default acl lists.
    """
    #Our version takes care of context as well
    config.add_request_method(has_permission, name = 'has_permission')
    config.add_request_method(context_effective_principals)
    #ACL registry must be created first
    config.include('arche.models.acl')
    config.include('arche.models.roles')
    config.register_roles(ROLE_ADMIN,
                          ROLE_EDITOR,
                          ROLE_VIEWER,
                          ROLE_OWNER,
                          ROLE_REVIEWER,
                          ROLE_EVERYONE,
                          ROLE_AUTHENTICATED)
    #ACL
    aclreg = config.registry.acl
    aclreg['default'] = 'inherit'
    #Private
    private = aclreg.new_acl('private', title = _("Private"))
    private.add(ROLE_ADMIN, ALL_PERMISSIONS)
    private.add(ROLE_OWNER, [PERM_VIEW, PERM_EDIT, PERM_DELETE])
    private.add(ROLE_EDITOR, [PERM_VIEW, PERM_EDIT, PERM_DELETE])
    private.add(ROLE_VIEWER, [PERM_VIEW])
    private.add(ROLE_REVIEWER, [PERM_REVIEW_CONTENT]) #May not be able to view
    #Public
    public = aclreg.new_acl('public', title = _("Public"))
    public.add(ROLE_ADMIN, ALL_PERMISSIONS)
    public.add(Everyone, [PERM_VIEW])
    public.add(ROLE_EDITOR, [PERM_VIEW, PERM_EDIT, PERM_DELETE])
    public.add(ROLE_REVIEWER, [PERM_REVIEW_CONTENT])
    #Review
    review = aclreg.new_acl('review', title = _("Review"))
    review.add(ROLE_ADMIN, ALL_PERMISSIONS)
    review.add(ROLE_OWNER, [PERM_VIEW])
    review.add(ROLE_EDITOR, [PERM_VIEW])
    review.add(ROLE_VIEWER, [PERM_VIEW])
    review.add(ROLE_REVIEWER, [PERM_VIEW, PERM_REVIEW_CONTENT])
    #User
    user_acl = config.registry.acl.new_acl('User', title = _("User"))
    user_acl.add(ROLE_ADMIN, [PERM_VIEW, PERM_EDIT, PERM_MANAGE_USERS,
                              PERM_MANAGE_SYSTEM, PERM_DELETE,
                              PERM_ACCESS_AUTH_SESSIONS])
    user_acl.add(ROLE_OWNER, [PERM_VIEW, PERM_EDIT, PERM_ACCESS_AUTH_SESSIONS])
    #Root
    aclreg['Root'] = 'public'
