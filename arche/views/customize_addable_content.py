from pyramid.view import view_config

from arche.views.base import DefaultEditForm
from arche.interfaces import IContent
from arche.security import PERM_MANAGE_SYSTEM


@view_config(context=IContent,
             name='customize_addable_content',
             permission=PERM_MANAGE_SYSTEM,
             renderer='arche:templates/form.pt')
class CustomizeAddableContentForm(DefaultEditForm):
    schema_name = 'customize_addable_content'
    type_name = "Content"

    def save_success(self, appstruct):
        if not appstruct['custom_addable']:
            del appstruct['custom_addable_types']
            del self.context.custom_addable_types
        return super(CustomizeAddableContentForm, self).save_success(appstruct)


def includeme(config):
    config.scan(__name__)