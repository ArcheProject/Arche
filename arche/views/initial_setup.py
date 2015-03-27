from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember

from arche.views.base import DefaultEditForm
from arche import security
from arche import _
from arche.interfaces import IInitialSetup


class InitialSetupForm(DefaultEditForm):
    schema_name = u'setup'
    title = _(u"Initial Setup")
    appstruct = lambda x: {}

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        self.context.setup_data = appstruct
        headers = remember(self.request, appstruct['userid'])
        return HTTPFound(location = self.request.resource_url(self.context), headers = headers)


def includeme(config):
    config.add_view(InitialSetupForm,
                    context = IInitialSetup,
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/initial_setup.pt')
