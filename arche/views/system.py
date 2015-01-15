from betahaus.viewcomponent import view_action
from betahaus.viewcomponent.interfaces import IViewGroup
from pyramid.renderers import render

from arche.interfaces import (IContextACL,
                              ILocalRoles,
                              IRoot,)
from arche.utils import (get_content_factories,
                         get_addable_content,
                         get_content_schemas,
                         get_content_views,
                         image_mime_to_title,
                         get_image_scales)
from arche.views.base import BaseView
from arche import security
from arche import _

common_titles = {False: _(u"No"),
                 True: _(u"Yes"),
                 security.Allow: _(u"Allow"),
                 security.Deny: _(u"Deny")}


class SystemInformationView(BaseView):

    def __call__(self):
        reg = self.request.registry
        vg = reg.queryUtility(IViewGroup, name = 'sysinfo')
        sysinfo_panels = []
        for (name, va) in vg.items():
            out = va(self.context, self.request, view = self)
            if out:
                sysinfo_panels.append({'id': name,
                                       'title': va.title,
                                       'body': out})
        return {'sysinfo_panels': sysinfo_panels}


@view_action('sysinfo', 'content_types',
             title = _(u"Content types"),
             permission = security.PERM_MANAGE_SYSTEM)
def content_types_panel(context, request, va, **kw):
    response = {
        'content_factories': get_content_factories(request.registry),
        'addable_content': get_addable_content(request.registry),
        'content_views': get_content_views(request.registry),
        'content_schemas': get_content_schemas(request.registry),
        'workflows': request.registry.workflows,
        'acl_iface': IContextACL,
        'local_roles_iface': ILocalRoles,
        }
    return render('arche:templates/sysinfo/content_types.pt', response, request = request)

@view_action('sysinfo', 'roles',
             title = _(u"Roles"),
             permission = security.PERM_MANAGE_SYSTEM)
def roles_pane(context, request, va, **kw):
    roles_registry = security.get_roles_registry(request.registry)
    response = {
        'roles_registry': roles_registry,
        'common_titles': common_titles,
        'role_titles': dict([(x, x.title) for x in roles_registry]),
        }
    return render('arche:templates/sysinfo/roles.pt', response, request = request)

@view_action('sysinfo', 'acl',
             title = _(u"ACL"),
             permission = security.PERM_MANAGE_SYSTEM)
def acl_panel(context, request, va, **kw):
    roles_registry = security.get_roles_registry(request.registry)
    response = {
        'acl_registry': security.get_acl_registry(request.registry),
        'role_titles': dict([(x, x.title) for x in roles_registry]),
        }
    return render('arche:templates/sysinfo/acl.pt', response, request = request)

@view_action('sysinfo', 'images',
             title = _(u"Images"),
             permission = security.PERM_MANAGE_SYSTEM)
def images_panel(context, request, va, **kw):
    response = {'mime_to_title': image_mime_to_title,
                'scales': get_image_scales(request.registry)}
    return render('arche:templates/sysinfo/images.pt', response, request = request)

def includeme(config):
    config.add_view(SystemInformationView,
                    context = IRoot,
                    name = 'sysinfo',
                    renderer = "arche:templates/sysinfo.pt",
                    permission = security.PERM_MANAGE_SYSTEM)
    config.scan('.system')
