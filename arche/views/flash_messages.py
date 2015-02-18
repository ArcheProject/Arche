from __future__ import unicode_literals

from pyramid.settings import asbool
from pyramid.response import Response

from arche.views.base import BaseView
from arche import security


class FlashMessagesView(BaseView):
    """ Ment to be used to append flash messages and then possibly load any results back in a template. """

    def __call__(self):
        params = self.request.params
        message = params.get('message', None)
        if message:
            msg_type = params.get('type', 'info')
            dismissable = asbool(params.get('dismissable', True))
            auto_destruct = asbool(params.get('auto_destruct', True))
            self.flash_messages.add(message,
                                    type = msg_type,
                                    dismissable = dismissable,
                                    auto_destruct = auto_destruct)
        return Response(self.flash_messages.render())


def includeme(config):
    config.add_route('flash_messages', '/__flash_messages__')
    config.add_view(FlashMessagesView,
                    route_name = 'flash_messages',
                    permission = security.Authenticated)
