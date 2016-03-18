from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.httpexceptions import HTTPForbidden

from arche.interfaces import IAPIKeyView, IViewInitializedEvent, IBaseView


class KeyAndTktAuthentication(AuthTktAuthenticationPolicy):
    """ Overrides unauthenticated_userid to provide the option of authenticating as a user
        with a specific API-key, possibly tied to an IP-address
    """

    def unauthenticated_userid(self, request):
        """ The userid key within the auth_tkt cookie."""
        #FIXME: Debug process?
        if 'userid' in request.params and 'apikey' in request.params:
            userid = request.params['userid']
            if request.root and userid in request.root['users']:
                request_key = request.params['apikey']
                apikey = getattr(request.root['users'][userid], 'apikey', object())
                if request_key == apikey:
                    request.is_apiuser = True
                    return userid
            #Should an exception be raised here?
        return super(KeyAndTktAuthentication, self).unauthenticated_userid(request)


def view_guard(view, event):
    if getattr(view.request, 'is_apiuser', False) and not IAPIKeyView.providedBy(view):
        raise HTTPForbidden("Authentication with API-keys aren't allowed for this view.")

def includeme(config):
    config.add_subscriber(view_guard, [IBaseView, IViewInitializedEvent])
