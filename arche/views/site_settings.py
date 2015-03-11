from pyramid.httpexceptions import HTTPFound

from arche import _
from arche.security import PERM_MANAGE_SYSTEM
from arche.views.base import DefaultEditForm


class SiteSettingsForm(DefaultEditForm):
    type_name = u'Root'
    schema_name = 'site_settings'
    title = _("Site settings")

    def appstruct(self):
        return dict(self.context.site_settings)

    def save_success(self, appstruct):
        self.context.site_settings = appstruct
        self.flash_messages.add(self.default_success)
        return HTTPFound(location = self.request.resource_url(self.context))


def includeme(config):
    config.add_view(SiteSettingsForm,
                    name = 'site_settings',
                    context = 'arche.interfaces.IRoot',
                    permission = PERM_MANAGE_SYSTEM,
                    renderer = 'arche:templates/form.pt')
