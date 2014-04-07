from pyramid.httpexceptions import HTTPFound

from arche.views.base import DefaultEditForm
from arche import security
from arche import _


class InitialSetupForm(DefaultEditForm):
    schema_name = u'setup'
    header = _(u"Welcome")
    appstruct = lambda x: {}

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        self.context.setup_data = appstruct
        return HTTPFound(location = self.request.resource_url(self.context))


def includeme(config):
    config.add_view(InitialSetupForm,
                    context = 'arche.interfaces.IInitialSetup',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/initial_setup.pt')
