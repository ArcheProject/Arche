import sys
import traceback

from pyramid.httpexceptions import HTTPClientError
from pyramid.httpexceptions import HTTPException
from pyramid.httpexceptions import HTTPFound
from pyramid.i18n import TranslationString
from pyramid.location import lineage

from arche.exceptions import ReferenceGuarded
from arche.security import NO_PERMISSION_REQUIRED
from arche.security import PERM_VIEW
from arche.views.base import BaseView
from arche import _
from arche import logger


_generic_exc_msg = _("generic_exception_explanation",
                     default = "Something isn't behaving the way it should. "
                     "The error has been logged. You may wish to contact "
                     "the person running this site about this error. "
                     "It's one of those things that should never happen. ")

class ExceptionView(BaseView):

    def __init__(self, context, request):
        """ Exception - context is the exception here. """
        super(ExceptionView, self).__init__(context, request)
        self.exc = context
        self.context = getattr(request, 'context', None)
        #self.request.response.status = getattr(self.exc, 'status', 500)
        if isinstance(self.exc, HTTPException):
            self.request.response.status_int = self.exc.code
        else:
            self.request.response.status_int = 500

    def __call__(self):
        response = {}
        response['debug'] = debug = self.request.registry.settings.get('arche.debug', False)
        exception_list = traceback.format_stack()
        exception_list = exception_list[:-2]
        exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
        exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
        exception_str = "Traceback (most recent call last):\n"
        exception_str += "".join(exception_list)
        if debug and not self.request.is_xhr:
            response['exception_str'] = exception_str
        else:
            logger.critical(exception_str)
        if self.request.response.status == 500:
            response['exc_msg'] = _generic_exc_msg
        else:
            msg = getattr(self.exc, 'message', "")
            response['exc_msg'] = self.request.localizer.translate(msg)
        return response


class NotFoundExceptionView(ExceptionView):

    def __call__(self):
        return {}


class ReferenceGuardedException(ExceptionView):

    def __call__(self):
        exc_context = None
        if self.request.has_permission(PERM_VIEW, self.exc.context):
            exc_context = self.exc.context
        return {'exc_context': exc_context, 'context': self.context, 'exc': self.exc}


class ForbiddenExceptionView(ExceptionView):

    def __call__(self):
        msg = getattr(self.exc, 'message', '')
        if isinstance(msg, TranslationString):
            msg = self.request.localizer.translate(msg)
        if not self.request.authenticated_userid:
            if msg:
                self.flash_messages.add(msg, type = 'danger', require_commit = False)
            if not msg:
                msg = _("Not allowed, perhaps you need to log in?")
                self.flash_messages.add(msg, type = 'warning', require_commit = False, auto_destruct = True)
            return HTTPFound(location = self.request.resource_url(self.root, 'login', query = {'came_from': self.request.url}))
        if self.context:
            for obj in lineage(self.context):
                if self.request.has_permission(PERM_VIEW, obj):
                    return {'ok_context': obj}
        return {'ok_context': None}


def includeme(config):
    config.add_forbidden_view(ForbiddenExceptionView,
                              xhr=False,
                              renderer = "arche:templates/exceptions/403.pt")
    config.add_notfound_view(NotFoundExceptionView,
                             xhr=False,
                             renderer = "arche:templates/exceptions/404.pt")
    #Added in pyramid 1.8, remove when 1.7 isn't supported.
    if hasattr(config, 'add_exception_view'):
        config.add_exception_view(
            ExceptionView,
            context=HTTPClientError,
            xhr=False,
            renderer = "arche:templates/exceptions/400.pt",)
        config.add_exception_view(
            ReferenceGuardedException,
            context=ReferenceGuarded,
            xhr=False,
            renderer="arche:templates/exceptions/reference_guarded.pt")
        config.add_exception_view(
            ExceptionView,
            xhr=False,
            renderer = "arche:templates/exceptions/generic.pt",)
    else:
        config.add_view(ExceptionView,
                        context=HTTPClientError,
                        xhr=False,
                        renderer="arche:templates/exceptions/400.pt",
                        permission = NO_PERMISSION_REQUIRED)
        config.add_view(ReferenceGuardedException,
                        context=ReferenceGuarded,
                        xhr=False,
                        renderer="arche:templates/exceptions/reference_guarded.pt",
                        permission=NO_PERMISSION_REQUIRED)
        config.add_view(ExceptionView,
                        context = Exception,
                        xhr=False,
                        renderer = "arche:templates/exceptions/generic.pt",
                        permission = NO_PERMISSION_REQUIRED)
