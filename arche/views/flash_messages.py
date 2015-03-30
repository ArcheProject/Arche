from __future__ import unicode_literals

from arche.views.base import BaseView
from arche import security


class FlashMessagesView(BaseView):
    """ Return flash messages as a json object """

    def __call__(self):
        result = []
        for flash in self.flash_messages.get_messages():
            msg = self.request.localizer.translate(flash.pop('msg', ''))
            result.append([msg, flash])
        return result


def includeme(config):
    config.add_route('flash_messages', '/flash_messages.json')
    config.add_view(FlashMessagesView,
                    route_name = 'flash_messages',
                    renderer = 'json',
                    permission = security.NO_PERMISSION_REQUIRED)
