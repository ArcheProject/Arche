""" Things like navigation, action menu etc. """
#from __future__ import unicode_literals

from betahaus.viewcomponent import view_action
from repoze.folder.interfaces import IFolder

from arche import _
from arche import security
from arche.interfaces import IContentView, IContextACL
from arche.interfaces import ILocalRoles
from arche.portlets import get_portlet_slots
from arche.utils import get_content_views
from arche.views.cut_copy_paste import can_paste
from arche.workflow import get_context_wf


@view_action('actionbar_main', 'wf',
             title = _("Workflow"),
             priority = 5)
def wf_menu(context, request, va, **kw):
    if not IContextACL.providedBy(context):
        return
    wf = get_context_wf(context)
    if wf:
        view = kw['view']
        return view.render_template('arche:templates/menus/workflow.pt', wf = wf)


@view_action('actionbar_main', 'view',
             title = _("View"),
             permission = security.PERM_VIEW,
             view_name = '',
             priority = 10)
@view_action('actionbar_main', 'edit',
             title = _("Edit"),
             permission = security.PERM_EDIT,
             view_name = 'edit',
             priority = 20)
@view_action('actionbar_main', 'contents',
             title = _("Contents"),
             permission = security.PERM_EDIT,#XXX: ?
             interface = IFolder,
             view_name = 'contents',
             priority = 30)
@view_action('actionbar_main', 'permissions',
             title = _("Permissions"),
             permission = security.PERM_MANAGE_USERS,#XXX: ?
             view_name = 'permissions',
             priority = 40,
             interface = ILocalRoles)
def actionbar_main_generic(context, request, va, **kw):
    return """<li><a href="%(url)s" alt="%(desc)s">%(title)s</a></li>""" % \
        {'url': request.resource_url(context, va.kwargs['view_name']),
         'title': va.title,
         'desc': va.kwargs.get('description', '')}

#Permission to add handled by content types!
@view_action('actionbar_main', 'add',
             title = _("Add"),
             priority = 50)
def add_menu(context, request, va, **kw):
    view = kw['view']
    return view.render_template('arche:templates/menus/add_content.pt')

@view_action('actionbar_main', 'actions',
             title = _("Actions"),
             permission = security.PERM_EDIT,#XXX: ?
             priority = 60)
def action_menu(context, request, va, **kw):
    view = kw['view']
    return view.render_template('arche:templates/menus/actions.pt')

@view_action('actionbar_right', 'user',
             title = _("User menu"),
             priority = 10)
def user_menu(context, request, va, **kw):
    if request.authenticated_userid:
        view = kw['view']
        return view.render_template('arche:templates/menus/user.pt')

@view_action('actionbar_right', 'site',
             title = _("Site menu"),
             permission = security.PERM_MANAGE_SYSTEM,#XXX: ?
             priority = 20)
def site_menu(context, request, va, **kw):
    view = kw['view']
    return view.render_template('arche:templates/menus/site.pt')


#FIXME: Silly to have section headers with permissions. That's going to end badly :)
@view_action('site_menu', 'system_overview',
             title = _("Overview"),
             description = _("Technichal system information"),
             priority = 10,
             permission = security.PERM_MANAGE_SYSTEM,
             section_header = _("System"),
             view_name = 'sysinfo',)
@view_action('site_menu', 'users',
             title = _("Users"),
             permission = security.PERM_MANAGE_USERS,
             section_header = _("Users & Groups"),
             priority = 20,
             view_name = 'users',)
@view_action('site_menu', 'groups',
             title = _("Groups"),
             permission = security.PERM_MANAGE_USERS,
             priority = 21,
             view_name = 'groups',)
@view_action('user_menu', 'logout',
             title = _("Logout"),
             priority = 20,
             view_name = 'logout',)
def generic_submenu_items(context, request, va, **kw):
    view = kw['view']
    out = ""
    section_header = va.kwargs.get('section_header', None)
    if section_header:
        out += """<li role="presentation" class="dropdown-header">%s</li>""" % section_header
    out += """<li><a href="%(url)s" title="%(desc)s">%(title)s</a></li>""" % \
        {'url': kw.get('url', request.resource_url(view.root, va.kwargs.get('view_name', ''))),
         'title': va.title,
         'desc': va.kwargs.get('description', '')}
    return out

@view_action('user_menu', 'profile',
             title = _("Profile"),
             priority = 10,)
def profile_item(context, request, va, **kw):
    userid = request.authenticated_userid
    if userid:
        view = kw['view']
        url = request.resource_url(view.root['users'], userid)
        return generic_submenu_items(context, request, va, url = url, **kw)

@view_action('actions_menu', 'delete',
             title = _("Delete"),
             priority = 20,
             permission = security.PERM_DELETE)
def delete_context(context, request, va, **kw):
    if context != kw['view'].root and not hasattr(context, 'is_permanent'):
        return """<li><a href="%(url)s">%(title)s</a></li>""" %\
            {'url': request.resource_url(context, 'delete'),
             'title': va.title}

@view_action('actions_menu', 'cut',
             title = _("Cut"),
             priority = 20,
             permission = security.PERM_DELETE)
def cut_context(context, request, va, **kw):
    if context != kw['view'].root and not hasattr(context, 'is_permanent'):
        return """<li><a href="%(url)s">%(title)s</a></li>""" %\
            {'url': request.resource_url(context, '__cut_context__'),
             'title': va.title}

@view_action('actions_menu', 'copy',
             title = _("Copy"),
             priority = 20,
             permission = security.PERM_VIEW) #FIXME: Permission?
def copy_context(context, request, va, **kw):
    #Copying objects with subobjects aren't supported yet, since subobjects and references need to be updated.
    if context != kw['view'].root and not len(context):
        return """<li><a href="%(url)s">%(title)s</a></li>""" %\
            {'url': request.resource_url(context, '__copy_context__'),
             'title': va.title}

@view_action('actions_menu', 'paste',
             title = _("Paste"),
             priority = 20)
def paste_context(context, request, va, **kw):
    view = kw['view']
    if can_paste(context, request, view):
        return """<li><a href="%(url)s">%(title)s</a></li>""" %\
            {'url': request.resource_url(context, '__paste_context__'),
             'title': va.title}

@view_action('actions_menu', 'manage_portlets',
             title = _("Manage portlets"),
             priority = 10,
             permission = security.PERM_MANAGE_SYSTEM)
def manage_portlets(context, request, va, **kw):
    if get_portlet_slots(request.registry):
        return """<li><a href="%(url)s">%(title)s</a></li>""" %\
                {'url': request.resource_url(context, 'manage_portlets'),
                 'title': va.title}

@view_action('actions_menu', 'selectable_views',
             priority = 30,
             permission = security.PERM_MANAGE_SYSTEM)
def selectable_views(context, request, va, **kw):
    if not hasattr(context, 'default_view'):
        return
    type_name = getattr(context,'type_name', None)
    selectable_views = {'view': _(u"Default")}
    views = get_content_views(request.registry)
    for (name, view_cls)in views.get(type_name, {}).items():
        selectable_views[name] = view_cls.title
    out = """<li role="presentation" class="dropdown-header">%s</li>\n""" % _("View selection")
    for (name, title) in selectable_views.items():
        selected = ""
        if context.default_view == name:
            selected = """<span class="glyphicon glyphicon-ok pull-right"></span>"""
        out += """<li><a href="%(url)s">%(title)s %(selected)s</a></li>""" %\
                {'url': request.resource_url(context, 'set_view', query = {'name': name}),
                 'title': title,
                 'selected': selected}
    return out

@view_action('actions_menu', 'view_settings',
             priority = 31,
             title = _(u"View settings"),
             permission = security.PERM_MANAGE_SYSTEM)
def view_settings(context, request, va, **kw):
    view = kw['view']
    if not IContentView.providedBy(view):
        return
    if view.settings_schema is not None:
        return """<li role="presentation" class="divider"></li>
            <li><a href="%(url)s">%(title)s</a></li>""" %\
            {'url': request.resource_url(context, 'view_settings'),
             'title': va.title}


def includeme(config):
    config.scan('arche.views.actions')
