from datetime import timedelta
from persistent import Persistent

from BTrees.LOBTree import LOBTree
from BTrees.OOBTree import OOBTree
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.httpexceptions import HTTPForbidden
from pyramid.interfaces import IRequest
from zope.component import adapter
from zope.interface import implementer

from arche.interfaces import IAPIKeyView
from arche.interfaces import IBase
from arche.interfaces import IBaseView
from arche.interfaces import IViewInitializedEvent
from arche.plugins.auth_sessions.interfaces import IAuthSessionData
from arche.utils import utcnow


class ExtendedSessionAuthenticationPolicy(SessionAuthenticationPolicy):
    """ Authentication based on either passing along params or
        using a session identified by a cookie.
    """

    def __init__(self, prefix='auth.', callback=None, debug=False):
        self.callback = callback
        self.prefix = prefix or ''
        self.userid_key = prefix + 'userid'
        self.session_key = prefix + 'session'
        self.debug = debug

    def remember(self, request, userid, **kw):
        """ Store a userid in the session."""
        request.session[self.userid_key] = userid
        asd = IAuthSessionData(request)
        ad = asd.new(userid, **kw)
        request.session[self.session_key] = ad.key
        return []

    def forget(self, request):
        """ Remove the stored userid from the session + disable the session data."""
        IAuthSessionData(request).close(logout = True)
        return []

    def _is_key_session(self, params):
        return 'userid' in params and 'key' in params and 'session' in params

    def _get_session_userid(self, request):
        if hasattr(request, '_kauth_userid'):
            return request._kauth_userid
        userid = request.params['userid']
        key = request.params['key']
        try:
            asession = int(request.params['session'])
        except ValueError: #pragma: no coverage
            return None
        asd = IAuthSessionData(request)
        try:
            ad = asd.sessions[userid][asession]
        except KeyError:
            return None
        if ad.api_key and ad.active and ad.api_key == key:
            request._kauth_userid = userid
            request._kauth_session_id = asession
            return userid
        return None

    def unauthenticated_userid(self, request):
        if self._is_key_session(request.params):
            return self._get_session_userid(request)
        return request.session.get(self.userid_key)

#    def authenticated_userid(self, request):
#        return super(ExtendedSessionAuthenticationPolicy, self).authenticated_userid(request)


@implementer(IAuthSessionData)
@adapter(IRequest)
class AuthSessionData(object):
    max_sessions = 5
    max_keep_days = 30
    default_max_valid = 60
    activity_update = 60
    userid_key = 'auth.userid'
    session_key = 'auth.session'

    def __init__(self, request):
        self.request = request
        try:
            self.sessions = request.root._auth_sessions
        except AttributeError:
            self.sessions = request.root._auth_sessions = OOBTree()
        self.max_sessions = request.registry.settings.get('arche.auth.max_sessions', self.max_sessions)
        self.max_keep_days = request.registry.settings.get('arche.auth.max_keep_days', self.max_keep_days)
        self.default_max_valid = request.registry.settings.get('arche.auth.default_max_valid', self.default_max_valid)
        self.activity_update = request.registry.settings.get('arche.auth.activity_update', self.activity_update)

    def get_active(self, userid = None):
        if userid is None:
            userid = self.request.authenticated_userid
        kuserid = getattr(self.request, '_kauth_userid', None)
        asession = getattr(self.request, '_kauth_session_id', None)
        ad = None
        if kuserid == None or asession == None:
            if userid != None:
                #Regular auth mechanism
                key = self.request.session.get(self.session_key, None)
                if key:
                    ad = self.sessions.get(userid, {}).get(key, None)
        else:
            ad = self.sessions.get(kuserid, {}).get(asession, None)
        if ad and ad.active:
            if ad.ip_locked and self.request.client_addr not in ad.ip_locked:
                raise HTTPForbidden("Session not allowed with this IP address")
            return ad

    def get_all_active(self, userid):
        results = []
        for ad in self.sessions.get(userid, {}).values():
            if ad.active:
                results.append(ad)
        return sorted(results, key=lambda x: x.last, reverse=True)

    def activity(self):
        ad = self.get_active()
        if ad:
            now = utcnow()
            if isinstance(ad.max_valid, int):
                if timedelta(minutes = ad.max_valid) + ad.last < now:
                    self.close(logout=True)
                    raise HTTPForbidden("Login expired")
            if ad.user_agent and ad.user_agent != self.request.user_agent:
                raise HTTPForbidden("User agent missmatches login info")
            if (now - ad.last) > timedelta(seconds = self.activity_update):
                ad.last = now
        if not ad and self.request.authenticated_userid:
            self._logout()
            raise HTTPForbidden("Logged out")

    def new(self, userid, **kw):
        data = {'ip': self.request.client_addr,
                'login': utcnow(),
                'last': utcnow(),
                'active': True,
                'user_agent': self.request.user_agent,
                'max_valid': self.default_max_valid}
        data.update(kw)
        if userid not in self.sessions:
            self.sessions[userid] = LOBTree()
        self.cleanup(userid)
        try:
            next_key = self.sessions[userid].maxKey() + 1
        except ValueError:
            next_key = 1
        self.sessions[userid][next_key] = ad = AuthData(key = next_key, **data)
        self.disable_inactive(userid)
        return ad

    def cleanup(self, userid, keep_days = None):
        """ Clean up old sessions for a specific userid.
            Will also clear active sessions if there's no recent activity.
        """
        if keep_days is None:
            keep_days = self.max_keep_days
        keep_timestamp = timedelta(days = keep_days)
        remove_ids = set()
        for ad in self.get_data(userid):
            if ad.last + keep_timestamp < utcnow():
                remove_ids.add(ad.key)
        for id in remove_ids:
            del self.sessions[userid][id]

    def disable_inactive(self, userid):
        """ In case threre's a setting with max allowed sessions,
            disable the ones with the oldest activity mark.
            Disable all sessions that shouldn't be active.
        """
        if self.default_max_valid:
            current = self.get_all_active(userid)
            for ad in current[self.max_sessions:]:
                ad.active = False
        #Should we check any sessions that might be marked as active but really have expired here?

    def _logout(self):
        if self.userid_key in self.request.session:
            del self.request.session[self.userid_key]

    def close(self, logout = False):
        ad = self.get_active()
        if ad:
            del self.request.session[self.session_key]
            ad.active = False
        if logout:
            self._logout()

    def inactivate(self, userid, session_id):
        sessions = self.sessions.get(userid, {})
        if session_id in sessions:
            sessions[session_id].active = False

    def get_data(self, userid):
        return self.sessions.get(userid, {}).values()


class AuthData(Persistent):
    title = ""
    key = None
    ip = None
    login = None
    last = None
    active = False
    max_valid = None
    user_agent = None
    api_key = None
    ip_locked = ()

    def __init__(self, title = "", key = None, ip = None, login = utcnow(),
                 last = utcnow(), active = True, max_valid = None,
                 user_agent = None, api_key = None, ip_locked = ()):
        self.title = title
        self.key = key
        self.ip = ip
        self.login = login
        self.last = last
        self.active = active
        self.max_valid = max_valid
        self.user_agent = user_agent
        self.api_key = api_key
        self.ip_locked = frozenset(ip_locked)


def view_guard(view, event):
    if getattr(view.request, '_kauth_userid', False) and\
            not isinstance(getattr(view, 'context', None), Exception) and\
            not IAPIKeyView.providedBy(view):
        raise HTTPForbidden("Authentication with API-keys aren't allowed for this view.")

def log_activity(view, event):
    if IBase.providedBy(getattr(view, 'context', None)):
        IAuthSessionData(view.request).activity()

#def login_subscriber():
#    login_kwargs = {}
#    if appstruct.get('keep_me_logged_in', False):
#        login_kwargs['max_valid'] = None


def includeme(config):
    """ Only include this if you want extended session-based authentication with tickets
    """
    config.add_subscriber(view_guard, [IBaseView, IViewInitializedEvent])
    config.add_subscriber(log_activity, [IBaseView, IViewInitializedEvent])
    config.registry.registerAdapter(AuthSessionData)
