""" Things like navigation, action menu etc. """
from betahaus.viewcomponent import view_action
from deform_autoneed import need_lib
from repoze.folder.interfaces import IFolder

from arche import _
from arche import security
from arche.interfaces import IContent
from arche.interfaces import IContentView
from arche.interfaces import IContextACL
from arche.interfaces import ILocalRoles
from arche.interfaces import IRoot
from arche.interfaces import ITrackRevisions
from arche.models.workflow import get_context_wf
from arche.portlets import get_portlet_slots
from arche.security import PERM_MANAGE_SYSTEM
from arche.utils import get_content_schemas
from arche.utils import get_content_views
from arche.views.cut_copy_paste import can_paste


def render_actionbar(view, **kw):
    """ Default actionbar - show for all authenticated users. """
    if view.request.authenticated_userid:
        return view.render_template('arche:templates/action_bar.pt')


def render_actionbar_admins(view, **kw):
    """ A version where the actionbar is only shown to admin users. """
    if view.request.authenticated_userid and view.request.has_permission(security.PERM_MANAGE_SYSTEM, view.context):
        return view.render_template('arche:templates/action_bar.pt')


@view_action('actionbar_main', 'wf',
             title=_("Workflow"),
             priority=5)
def wf_menu(context, request, va, **kw):
    if not IContextACL.providedBy(context):
        return
    wf = get_context_wf(context)
    if wf:
        view = kw['view']
        transitions = tuple(wf.get_transitions(request))
        if transitions or request.has_permission(security.PERM_EDIT, context):
            return view.render_template('arche:templates/menus/workflow.pt', wf=wf, transitions=transitions)


@view_action('actionbar_main', 'view',
             title=_("View"),
             permission=security.PERM_VIEW,
             priority=10)
def actionbar_view(context, request, va, **kw):
    candidates = set(['', 'view'])
    for name in get_content_views(request.registry).get(context.type_name, {}):
        candidates.add(name)
    active_cls = request.view_name in candidates and 'active' or ''
    return """<li class="%(active_cls)s"><a href="%(url)s">%(title)s</a></li>""" % \
           {'url': request.resource_url(context),
            'active_cls': active_cls,
            'title': request.localizer.translate(va.title),}


@view_action('actionbar_main', 'contents',
             title=_("Contents"),
             permission=security.PERM_EDIT,  # XXX: ?
             interface=IFolder,
             view_name='contents',
             priority=30)
@view_action('actionbar_main', 'permissions',
             title=_("Permissions"),
             permission=security.PERM_MANAGE_USERS,  # XXX: ?
             view_name='permissions',
             priority=40,
             interface=ILocalRoles)
def actionbar_main_generic(context, request, va, **kw):
    active_cls = request.view_name == va.kwargs['view_name'] and 'active' or ''
    return """<li class="%(active_cls)s"><a href="%(url)s" title="%(desc)s">%(title)s</a></li>""" % \
           {'url': request.resource_url(context, va.kwargs['view_name']),
            'title': request.localizer.translate(va.title),
            'active_cls': active_cls,
            'desc': va.kwargs.get('description', '')}


@view_action('actionbar_main', 'edit',
             title=_("Edit"),
             permission=security.PERM_EDIT,
             view_name='edit',
             priority=20)
def edit_actionbar(context, request, va, **kw):
    try:
        get_content_schemas(request.registry)[getattr(context, 'type_name', None)]['edit']
    except KeyError:
        return
    return actionbar_main_generic(context, request, va, **kw)


# Permission to add handled by content types!
@view_action('actionbar_main', 'add',
             title=_("Add"),
             priority=50)
def add_menu(context, request, va, **kw):
    view = kw['view']
    can_customize_addable = IContent.providedBy(context) and \
                            request.has_permission(PERM_MANAGE_SYSTEM, context) and \
                            tuple(request.addable_content(context, restrict=False, check_perm=False))
    is_customized = can_customize_addable and getattr(context, 'custom_addable', False) or False
    addable_content = tuple(request.addable_content(context))
    if addable_content or can_customize_addable:
        return view.render_template('arche:templates/menus/add_content.pt',
                                    addable_content=addable_content,
                                    can_customize_addable=can_customize_addable,
                                    is_customized=is_customized)


@view_action('actionbar_main', 'actions',
             title=_("Actions"),
             priority=60)
def action_menu(context, request, va, **kw):
    if request.authenticated_userid:
        view = kw['view']
        actions_output = view.render_view_group('actions_menu')
        if actions_output:
            return view.render_template('arche:templates/menus/actions.pt', actions_output=actions_output)


@view_action('actionbar_main', 'selectable_templates',
             title=_("Templates"),
             permission=security.PERM_MANAGE_SYSTEM,
             priority=70)
def template_menu(context, request, va, **kw):
    if not hasattr(context, 'default_view'):
        return
    rcontext = getattr(request, 'context', None)
    if getattr(rcontext, 'delegate_view', None):
        return
    views = get_content_views(request.registry).get(context.type_name, {}).items()
    if views:
        view = kw['view']
        return view.render_template('arche:templates/menus/templates.pt', views=views)


@view_action('nav_right', 'user',
             title=_("User menu"),
             priority=10)
def user_menu(context, request, va, **kw):
    if request.authenticated_userid:
        view = kw['view']
        return view.render_template('arche:templates/menus/user.pt')


@view_action('nav_right', 'site',
             title=_("Site menu"),
             permission=security.PERM_MANAGE_SYSTEM,  # XXX: ?
             priority=20)
def site_menu(context, request, va, **kw):
    view = kw['view']
    return view.render_template('arche:templates/menus/site.pt')


@view_action('nav_right', 'login',
             title=_("Login"),
             priority=10)
def login_link(context, request, va, **kw):
    if request.authenticated_userid is None and \
            IRoot.providedBy(request.root) and \
            request.root.site_settings.get('show_login_link', True):
        need_lib('deform')
        data = {'href': request.resource_url(request.root, 'login')}
        return """<li><a %s>%s</a></li>""" % \
               (' '.join(['%s="%s"' % (k, v) for (k, v) in data.items()]),
                request.localizer.translate(va.title))


@view_action('nav_right', 'register',
             title=_("Register"),
             priority=20)
def register_link(context, request, va, **kw):
    # FIXME: Check registration form.
    if request.authenticated_userid is None and request.has_permission(security.PERM_REGISTER, request.root):
        return """<li><a href="%s">%s</a></li>""" % \
               (request.resource_url(request.root, 'register'),
                request.localizer.translate(va.title))


# FIXME: Silly to have section headers with permissions. That's going to end badly :)
@view_action('site_menu', 'site_settings',
             title=_("Settings"),
             priority=10,
             permission=security.PERM_MANAGE_SYSTEM,
             view_name='site_settings')
@view_action('site_menu', 'users',
             title=_("Users"),
             permission=security.PERM_MANAGE_USERS,
             priority=20,
             view_name='users', )
@view_action('site_menu', 'groups',
             title=_("Groups"),
             permission=security.PERM_MANAGE_USERS,
             priority=21,
             view_name='groups', )
@view_action('user_menu', 'logout',
             title=_("Logout"),
             priority=50,
             divider=True,
             view_name='logout', )
def generic_submenu_items(context, request, va, **kw):
    view = kw['view']
    out = ""
    section_header = va.kwargs.get('section_header', None)
    if section_header:
        out += """<li role="presentation" class="dropdown-header">%s</li>""" % section_header
    if va.kwargs.get('divider', None):
        out += """<li role="presentation" class="divider"></li>"""
    out += """<li><a href="%(url)s" title="%(desc)s">%(title)s</a></li>""" % \
           {'url': kw.get('url', request.resource_url(view.root, va.kwargs.get('view_name', ''))),
            'title': request.localizer.translate(va.title),
            'desc': va.kwargs.get('description', '')}
    return out


@view_action('user_menu', 'profile',
             title=_("Profile"),
             priority=10, )
@view_action('user_menu', 'change_password',
             title=_("Change password"),
             priority=20,
             view_name='change_password', )
def generic_profile_items(context, request, va, **kw):
    if request.authenticated_userid and request.profile:
        url = request.resource_url(request.profile, va.kwargs.get('view_name', ''))
        return generic_submenu_items(context, request, va, url=url, **kw)


@view_action('user_menu', 'validate_email',
             title=_("Validate email"),
             priority=25,
             view_name='validate_email')
def validate_email_action(context, request, va, **kw):
    try:
        if not request.profile.email_validated and request.profile.email:
            return generic_profile_items(context, request, va, **kw)
    except AttributeError:
        pass


@view_action('actions_menu', 'delete',
             title=_("Delete"),
             priority=20,
             permission=security.PERM_DELETE)
def delete_context(context, request, va, **kw):
    if context != kw['view'].root and not hasattr(context, 'is_permanent'):
        return """<li><a href="%(url)s">%(title)s</a></li>""" % \
               {'url': request.resource_url(context, 'delete'),
                'title': request.localizer.translate(va.title)}


@view_action('actions_menu', 'cut',
             title=_("Cut"),
             priority=20,
             permission=security.PERM_DELETE)
def cut_context(context, request, va, **kw):
    if context != kw['view'].root and not hasattr(context, 'is_permanent'):
        return """<li><a href="%(url)s">%(title)s</a></li>""" % \
               {'url': request.resource_url(context, '__cut_context__'),
                'title': request.localizer.translate(va.title)}


@view_action('actions_menu', 'copy',
             title=_("Copy"),
             priority=20,
             permission=security.PERM_VIEW)  # FIXME: Permission?
def copy_context(context, request, va, **kw):
    if context != kw['view'].root:
        return """<li><a href="%(url)s">%(title)s</a></li>""" % \
               {'url': request.resource_url(context, '__copy_context__'),
                'title': request.localizer.translate(va.title)}


@view_action('actions_menu', 'paste',
             title=_("Paste"),
             priority=20)
def paste_context(context, request, va, **kw):
    view = kw['view']
    if can_paste(context, request, view):
        return """<li><a href="%(url)s">%(title)s</a></li>""" % \
               {'url': request.resource_url(context, '__paste_context__'),
                'title': request.localizer.translate(va.title)}


@view_action('actions_menu', 'rename',
             title=_("Rename"),
             permission=security.PERM_MANAGE_SYSTEM,
             priority=25)
def rename_context(context, request, va, **kw):
    if context != kw['view'].root and not hasattr(context, 'is_permanent'):
        return """<li><a href="%(url)s">%(title)s</a></li>""" % \
               {'url': request.resource_url(context, '__rename_context__'),
                'title': request.localizer.translate(va.title)}


@view_action('actions_menu', 'manage_portlets',
             title=_("Manage portlets"),
             priority=10,
             permission=security.PERM_MANAGE_SYSTEM)
def manage_portlets(context, request, va, **kw):
    if get_portlet_slots(request.registry):
        return """<li><a href="%(url)s">%(title)s</a></li>""" % \
               {'url': request.resource_url(context, 'manage_portlets'),
                'title': request.localizer.translate(va.title)}


@view_action('actions_menu', 'revisions',
             title=_("Revisions"),
             permission=security.PERM_MANAGE_SYSTEM,
             interface=ITrackRevisions,
             priority=30)
def revisions_context(context, request, va, **kw):
    return """<li><a href="%(url)s">%(title)s</a></li>""" % \
           {'url': request.resource_url(context, '__revisions__'),
            'title': request.localizer.translate(va.title)}


@view_action('actions_menu', 'delegate_view',
             priority=35,
             permission=security.PERM_MANAGE_SYSTEM)
def delegate_view(context, request, va, **kw):
    rcontext = getattr(request, 'context', None)
    if getattr(rcontext, 'delegate_view', None):
        return """<li class="divider"></li><li><a href="%s">%s</a></li>""" % \
               (request.resource_url(rcontext, 'set_delegate_view', query={'name': ''}),
                request.localizer.translate(_('Unset delegated view')))
        # FIXME: Experimental feature, add later
        # if hasattr(context, 'delegate_view'):
        #    return """<li class="divider"></li><li><a href="%s">%s</a></li>""" %\
        #        (request.resource_url(rcontext, 'pick_delegate_view'), _('Delegate view&#0133;'))


@view_action('actions_menu', 'view_settings',
             priority=31,
             title=_(u"View settings"),
             permission=security.PERM_MANAGE_SYSTEM)
def view_settings(context, request, va, **kw):
    #FIXME: We should probably remove this, it isn't used and was never a good feature...
    view = kw['view']
    if not IContentView.providedBy(view):
        return
    if view.settings_schema is not None:
        return """<li role="presentation" class="divider"></li>
            <li><a href="%(url)s">%(title)s</a></li>""" % \
               {'url': request.resource_url(context, 'view_settings'),
                'title': request.localizer.translate(va.title)}


def includeme(config):
    config.scan('arche.views.actions')
