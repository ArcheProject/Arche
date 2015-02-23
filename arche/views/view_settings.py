from BTrees.OOBTree import OOBTree
from colander import null
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound

from arche.utils import get_content_views
from arche.views.base import BaseForm
from arche import security


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

    def get_schema(self):
        if self.view.settings_schema is not None:
            return self.view.settings_schema()
        msg = "This view has no settings"
        raise HTTPForbidden(msg)

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        #Must be an adapter later on?
        #remove all non-valid data - is this an okay way to do this?
        keys = set(appstruct.keys())
        for k in keys:
            if appstruct[k] in (null, '', None):
                appstruct.pop(k, None)
        self.context.__view_settings__ = OOBTree(appstruct)
        return HTTPFound(location = self.request.resource_url(self.context))


def includeme(config):
    config.add_view(ViewSettingsView,
                    name = 'view_settings',
                    permission = security.PERM_MANAGE_SYSTEM,
                    renderer = "arche:templates/form.pt",
                    context = 'arche.interfaces.IContent') #FIXME: Is this correct?

