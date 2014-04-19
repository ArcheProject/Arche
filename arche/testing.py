
from pyramid.authentication import CallbackAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy


def setup_security(config, userid = None, debug = True):
    from arche.security import groupfinder
    config.set_authorization_policy(ACLAuthorizationPolicy())
    ap = CallbackAuthenticationPolicy()
    ap.debug = debug
    ap.unauthenticated_userid = lambda request: userid
    ap.callback = groupfinder
    config.set_authentication_policy(ap)
    config.include('arche.override_perm_methods')
