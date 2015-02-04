import sys
import traceback

from pyramid.httpexceptions import HTTPFound

from arche.security import NO_PERMISSION_REQUIRED
from arche.views.base import BaseView
from arche import _
from arche import logger


class ExceptionView(BaseView):

    def __init__(self, context, request):
        """ Exception - context is the exception here. """
        super(ExceptionView, self).__init__(context, request)
        self.exc = context
        self.context = getattr(request, 'context', None)
        #Make sure the response status code is some form of exception
        self.request.response.status = getattr(self.exc, 'code', 500)

    def __call__(self):
        response = {}
        response['debug'] = debug = self.request.registry.settings.get('arche.debug', False)
        if debug:
            exception_list = traceback.format_stack()
            exception_list = exception_list[:-2]
            exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
            exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
            exception_str = "Traceback (most recent call last):\n"
            exception_str += "".join(exception_list)
            response['exception_str'] = exception_str
        else:
            logger.critical(self.exc)
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
