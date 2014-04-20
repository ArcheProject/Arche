from arche.views.base import DefaultEditForm
from arche.security import PERM_MANAGE_USERS
from arche.schemas import permissions_schema_factory
from arche import _


class PermissionsForm(DefaultEditForm):

    @property
    def heading(self):
        return _("Local permissions for ${title}",
                 mapping = {'title': self.context.title})

    def __call__(self):
        self.schema = permissions_schema_factory(self.context, self.request, self)
        return super(PermissionsForm, self).__call__()

    def appstruct(self):
        """ Default values differ in permissions form, since local roles is used.
        """
        return self.context.local_roles

    def save_success(self, appstruct):
        #Change appstruct to set local_roles instead
        appstruct = {'local_roles': appstruct}
        return super(PermissionsForm, self).save_success(appstruct)


def includeme(config):
    config.add_view(PermissionsForm,
                    name = 'permissions',
                    context = 'arche.interfaces.IContent',
                    permission = PERM_MANAGE_USERS, #FIXME: Admin
                    renderer = 'arche:templates/form.pt')
