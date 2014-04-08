from pyramid.httpexceptions import HTTPFound

from arche.views.base import BaseForm
from arche.schemas import PermissionsSchema
from arche.utils import get_content_schemas
from arche.security import NO_PERMISSION_REQUIRED
from arche import _


class PermissionsForm(BaseForm):
    schema_name = u'permissions'
    heading = _("Permissions")

    def get_schema_factory(self, type_name, schema_name):
        """ Allow custom delete schemas here, otherwise just use the default one. """
        schema = get_content_schemas(self.request.registry).get(self.type_name, {}).get(self.schema_name)
        if not schema:
            return PermissionsSchema

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        print appstruct
        self.context.update(**appstruct)
        return HTTPFound(location = self.request.resource_url(self.context))


def includeme(config):
    config.add_view(PermissionsForm,
                    name = 'permissions',
                    context = 'arche.interfaces.IBase',
                    permission = NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
