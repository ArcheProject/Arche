from logging import getLogger

from pyramid.httpexceptions import HTTPFound

from arche.security import NO_PERMISSION_REQUIRED
from arche.views.base import BaseView
from arche import _

_log = getLogger(__name__)


class ExceptionView(BaseView):

    def __init__(self, context, request):
        """ Exception - context is the exception here. """
        super(ExceptionView, self).__init__(context, request)
        self.exc = context
        self.context = request.context

    def __call__(self):
        response = {}
        response['debug'] = debug = self.request.registry.settings.get('arche.debug', False)
        if not debug:
            _log.critical(self.exc)
        return response


class NotFoundExceptionView(ExceptionView):

    def __call__(self):
        return {}


class ForbiddenExceptionView(ExceptionView):

    def __call__(self):
        if not self.request.authenticated_userid:
            msg = _("Not allowed, perhaps you need to log in?")
            self.flash_messages.add(msg, type = 'warning')
            return HTTPFound(location = self.request.resource_url(self.root, 'login'))
        return {}


def includeme(config):
    config.add_forbidden_view(ForbiddenExceptionView,
                              renderer = "arche:templates/exceptions/403.pt")
    config.add_notfound_view(NotFoundExceptionView,
                             renderer = "arche:templates/exceptions/404.pt")
    config.add_view(ExceptionView,
                    context = Exception,
                    renderer = "arche:templates/exceptions/generic.pt",
                    permission = NO_PERMISSION_REQUIRED)
