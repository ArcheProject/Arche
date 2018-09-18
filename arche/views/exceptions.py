import sys
import traceback

from pyramid.httpexceptions import HTTPClientError
from pyramid.httpexceptions import HTTPException
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.i18n import TranslationString
from pyramid.location import lineage

from arche import _
from arche import logger
from arche.exceptions import ReferenceGuarded
from arche.security import PERM_VIEW
from arche.views.base import BaseView


_generic_exc_msg = _("generic_exception_explanation",
                     default="Something isn't behaving the way it should. "
                             "The error has been logged. You may wish to contact "
                             "the person running this site about this error. "
                             "It's one of those things that should never happen. ")


class ExceptionView(BaseView):

    def __init__(self, context, request):
        """ Exception - context is the exception here. """
        super(ExceptionView, self).__init__(context, request)
        self.exc = context
        self.context = getattr(request, 'context', None)
        if isinstance(self.exc, HTTPException):
            self.request.response.status_int = self.exc.code
        else:
            self.request.response.status_int = 500

    def __call__(self):
        if self.request.is_xhr:
            return json_format_exc(self.request, self.exc)
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


class ReferenceGuardedException(ExceptionView):

    def __call__(self):
        exc_context = None
        if self.request.has_permission(PERM_VIEW, self.exc.context):
            exc_context = self.exc.context
        return {'exc_context': exc_context, 'context': self.context, 'exc': self.exc}


class ForbiddenExceptionView(ExceptionView):

    def __call__(self):
        if self.request.is_xhr:
            return json_format_exc(self.request, self.exc)
        msg = getattr(self.exc, 'message', '')
        if isinstance(msg, TranslationString):
            msg = self.request.localizer.translate(msg)
        if not self.request.authenticated_userid:
            if msg:
                self.flash_messages.add(msg, type='danger', require_commit=False)
            if not msg:
                msg = _("Not allowed, perhaps you need to log in?")
                self.flash_messages.add(msg, type='warning', require_commit=False,
                                        auto_destruct=True)
            return HTTPFound(location=self.request.resource_url(self.root, 'login', query={
                'came_from': self.request.url}))
        if self.context:
            for obj in lineage(self.context):
                if self.request.has_permission(PERM_VIEW, obj):
                    return {'ok_context': obj}
        return {'ok_context': None}


class UnauthorizedExceptionView(ExceptionView):

    def __call__(self):
        if self.request.is_xhr:
            return json_format_exc(self.request, self.exc)
        msg = getattr(self.exc, 'message', '')
        if not msg:
            msg = _("Not allowed, perhaps you need to log in?")
        if isinstance(msg, TranslationString):
            msg = self.request.localizer.translate(msg)
        if msg:
            self.flash_messages.add(msg, type='danger', require_commit=False, auto_destruct=True)
        return HTTPFound(location=self.request.resource_url(self.root, 'login', query={
            'came_from': self.request.url}))


def json_format_exc(request, exc):
    """ Return a json representation of the exception.
        If the exception has a __json__ method, use that one as base
    """
    message = getattr(exc, 'message', None)
    detail = getattr(exc, 'detail', None)
    if detail and not message:
        message = detail
    if isinstance(message, TranslationString):
        message = request.localizer.translate(message)
    title = getattr(exc, 'title', None)
    if title is None:
        title = _("Application error")
    if isinstance(title, TranslationString):
        title = request.localizer.translate(title)
    response = {
        'body': getattr(exc, 'body', None),  # Some exceptions have html bodies
        'message': message,  # Some have plaintext...
        'code': getattr(exc, 'status_int', 500),  # Some have codes
        'title': title  # And some have titles
    }
    try:
        response.update(exc.__json__(request))
    except AttributeError:
        pass
    return response


def includeme(config):
    # 403 regular
    config.add_forbidden_view(
        ForbiddenExceptionView,
        xhr=False,
        renderer="arche:templates/exceptions/403.pt"
    )
    # 403 xhr
    config.add_forbidden_view(
        ForbiddenExceptionView,
        xhr=True,
        renderer="json"
    )
    # 404 regular
    config.add_notfound_view(
        ExceptionView,
        xhr=False,
        renderer="arche:templates/exceptions/404.pt"
    )
    # 404 xhr
    config.add_notfound_view(
        ExceptionView,
        xhr=True,
        renderer="json"
    )
    # 401
    config.add_exception_view(
        UnauthorizedExceptionView,
        context=HTTPUnauthorized)
    # Other 400
    config.add_exception_view(
        ExceptionView,
        context=HTTPClientError,
        xhr=False,
        renderer="arche:templates/exceptions/400.pt", )
    # Reference guarded
    config.add_exception_view(
        ReferenceGuardedException,
        context=ReferenceGuarded,
        xhr=False,
        renderer="arche:templates/exceptions/reference_guarded.pt")
    # Catch all regular get
    config.add_exception_view(
        ExceptionView,
        xhr=False,
        renderer="arche:templates/exceptions/generic.pt", )
    # Catch all xhr
    config.add_exception_view(
        ExceptionView,
        xhr=True,
        renderer="json", )
