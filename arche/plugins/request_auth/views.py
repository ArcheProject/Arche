from pyramid.httpexceptions import HTTPBadRequest
from pyramid.view import view_config
from colander import Invalid

from arche.interfaces import IRoot
from arche.plugins.request_auth.exceptions import ConsumeTokenError
from arche.views.base import APIKeyViewMixin
from arche.views.base import BaseView
from .interfaces import IRequestSession


@view_config(context = IRoot, name = 'request_session', renderer = 'json')
class CreateTokenView(BaseView, APIKeyViewMixin):

    def __call__(self):
        """ Create a new session from POST data

            Example post:
            curl -X POST --data "userid=admin&client_ip=127.0.0.1&redirect_url=http://localhost:6543/users" \
                http://localhost:6543/request_session
        """
        rs = IRequestSession(self.root)
        try:
            url = rs.new_from_request(self.request)
            return {'url': url}
        except Invalid as exc:
            raise exc


@view_config(context=IRoot, name='_t_auth')
def consume_token_view(request, context):
    """ Consume session and redirect to wherever the session was set to redirect to.
    """
    rs = IRequestSession(context)
    try:
        return rs.consume_from_request(request)
    except ConsumeTokenError as exc:
        if request.registry.settings.get('arche.debug', False):
            raise
        raise HTTPBadRequest(exc.message)


def includeme(config):
    config.scan(__name__)
