from pyramid.httpexceptions import HTTPFound
from pyramid.security import NO_PERMISSION_REQUIRED

from arche.interfaces import IRoot
from arche.views.base import BaseView
from arche import _


class LanguagesView(BaseView):

    def __call__(self):
        lang = self.request.GET.get('lang', None)
        if lang in self.context.site_settings.get('languages', ()):
            msg = _("Language set to ${selected_lang}",
                    mapping = {'selected_lang': lang})
            self.flash_messages.add(msg)
            self.request.response.set_cookie('_LOCALE_', value = lang)
        url = self.request.GET.get('came_from', self.request.resource_url(self.root))
        return HTTPFound(location = url, headers = self.request.response.headers)


def includeme(config):
    config.add_view(
        LanguagesView,
        name='set_language',
        context=IRoot,
        permission=NO_PERMISSION_REQUIRED
    )
