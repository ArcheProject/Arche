from pyramid.httpexceptions import HTTPFound
from pyramid.decorator import reify
from BTrees.OOBTree import OOBTree

from arche.utils import get_content_views
from arche.views.base import BaseForm
from arche import security
from arche import _


class ViewSettingsView(BaseForm):

    @reify
    def view(self):
        """ The view we're working on.
        """
        content_views = get_content_views(self.request.registry).get(self.context.type_name, None)
        if content_views:
            name = getattr(self.context, 'default_view')
            return content_views.get(name, None)

    def appstruct(self):
        return dict(getattr(self.context, '__view_settings__', {}))

    def __call__(self):
        if self.view.settings_schema is not None:
            self.schema = self.view.settings_schema()
            return super(BaseForm, self).__call__()
        self.flash_messages.add(_("This view has no settings"), type = 'danger')
        return HTTPFound(location = self.request.resource_url(self.context))

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        #Must be an adapter later on
        self.context.__view_settings__ = OOBTree(appstruct)
        return HTTPFound(location = self.request.resource_url(self.context))


def includeme(config):
    config.add_view(ViewSettingsView,
                    name = 'view_settings',
                    permission = security.PERM_MANAGE_SYSTEM,
                    renderer = "arche:templates/form.pt",
                    context = 'arche.interfaces.IContent') #FIXME: Is this correct?

