""" Things like navigation, action menu etc. """
#from __future__ import unicode_literals

from betahaus.viewcomponent import view_action

from arche import security
from arche import _


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
             view_name = 'contents',
             priority = 30)
@view_action('actionbar_main', 'permissions',
             title = _("Permissions"),
             permission = security.PERM_MANAGE_USERS,#XXX: ?
             view_name = 'permissions',
             priority = 40)
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
    out += """<li><a href="%(url)s" alt="%(desc)s">%(title)s</a></li>""" % \
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


def includeme(config):
    config.scan('arche.views.actions')
