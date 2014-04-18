

from arche.views.base import BaseView
from arche.interfaces import IRoot
from arche.utils import (get_content_factories,
                         get_content_schemas,
                         get_content_views)
from arche import security
from arche import _

common_titles = {False: _(u"No"),
                 True: _(u"Yes"),
                 security.Allow: _(u"Allow"),
                 security.Deny: _(u"Deny")}

class SystemInformationView(BaseView):

    def __call__(self):
        reg = self.request.registry
        roles_registry = security.get_roles_registry(reg)
        response = dict(
            content_views = get_content_views(reg),
            content_schemas = get_content_schemas(reg),
            content_factories = get_content_factories(reg),
            roles_registry = roles_registry,
            acl_registry = security.get_acl_registry(reg),
            common_titles = common_titles,
            role_titles = dict([(x, x.title) for x in roles_registry])
        )
        return response


def includeme(config):
    config.add_view(SystemInformationView,
                    context = IRoot,
                    name = 'sysinfo',
                    renderer = "arche:templates/sysinfo.pt",
                    permission = security.PERM_MANAGE_SYSTEM)
