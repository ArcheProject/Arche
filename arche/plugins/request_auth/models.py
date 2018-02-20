import string
from datetime import timedelta
from random import choice

from BTrees.OOBTree import OOBTree
from pyramid.httpexceptions import HTTPFound
from pyramid.security import remember
from zope.component import adapter
from zope.interface import implementer

from arche import _
from arche.events import WillLoginEvent
from arche.interfaces import IRoot
from arche.plugins.request_auth.exceptions import ConsumeTokenError
from arche.utils import AttributeAnnotations
from arche.utils import utcnow
from .interfaces import IRequestSession


@adapter(IRoot)
@implementer(IRequestSession)
class RequestSession(AttributeAnnotations):
    attr_name = '_request_auth_session'

    def new(self, request, userid,
            client_ip = '',
            login_max_valid = 30,
            link_valid = 20,
            redirect_url = ''):
        link_valid = utcnow() + timedelta(seconds = link_valid)
        token = ''.join([choice(string.ascii_letters + string.digits) for x in range(50)])
        if not redirect_url:
            # I.e. Root
            redirect_url = request.resource_url(self.context)
        obj = OOBTree(dict(client_ip = client_ip,
                      login_max_valid = login_max_valid,
                      link_valid = link_valid,
                      token = token,
                      redirect_url = redirect_url))
        self[userid] = obj
        return request.resource_url(self.context, '_t_auth', token)

    def new_from_request(self, request):
        #Will raise colander invalid if something goes wrong
        data = self.get_data(request)
        return self.new(request, **data)

    def get_data(self, request):
        schema = request.get_schema(self.context, 'Auth', 'request_session')
        return schema.deserialize(request.POST)

    def consume(self, request, userid):
        """ Consume the link. Post-validation function
            to simply return the redirect and fire all events.
        """
        data = self.pop(userid)
        redirect_url = data.get('redirect_url', None)
        user = self.context.get('users', {}).get(userid, None)
        if user:
            event = WillLoginEvent(user, request = request)
            request.registry.notify(event)
        headers = remember(request, userid, max_valid = data['login_max_valid'])
        url = redirect_url and redirect_url or request.resource_url(self.context)
        return HTTPFound(location = url, headers = headers)

    def consume_from_request(self, request):
        if not request.subpath:
            raise ConsumeTokenError("No token")
        token = request.subpath[0]
        userid = None
        for (name, obj) in self.items():
            if token == obj.get('token', object()):
                userid = name
                break
        self.validate(userid, token, request.client_addr)
        return self.consume(request, userid)

    def validate(self, userid, token, ip_addr):
        try:
            assert userid, _("Token not found or used already")
            assert userid in self, _("No token related to userid ${userid}",
                                     mapping = {'userid': userid})
            data = self[userid]
            assert utcnow() < data['link_valid'], _("Link expired")
            assert token == data['token'] #Is this even needed since it wouldn't be found otherwise?
            assert ip_addr == data['client_ip'], _("IP address doesn't match")
        except AssertionError as exc:
            raise ConsumeTokenError(str(exc))


def includeme(config):
    config.registry.registerAdapter(RequestSession)
