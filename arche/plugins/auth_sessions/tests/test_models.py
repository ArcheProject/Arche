from unittest import TestCase

from datetime import timedelta

from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.interfaces import IAuthenticationPolicy
from zope.interface.verify import verifyClass, verifyObject

from arche.plugins.auth_sessions.interfaces import IAuthSessionData
from arche.utils import utcnow
from arche.security import groupfinder
from arche.testing import barebone_fixture
from arche.api import User


class ExtendedSessionAuthenticationPolicyTests(TestCase):
    
    def setUp(self):
        self.request = testing.DummyRequest(client_addr = '127.0.0.1', user_agent = 'Testing Browser')
        self.config = testing.setUp(request = self.request)
        self.config.registry.settings['arche.authn_factory'] = 'arche.plugins.auth_sessions.authn_factory'
        self.config.include('arche.plugins.auth_sessions.models')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.plugins.auth_sessions.models import ExtendedSessionAuthenticationPolicy
        return ExtendedSessionAuthenticationPolicy

    def test_validate_cls(self):
        self.failUnless(verifyClass(IAuthenticationPolicy, self._cut))

    def test_validate_obj(self):
        self.failUnless(verifyObject(IAuthenticationPolicy, self._cut()))

    def _fixture(self):
        root = barebone_fixture(self.config)
        root['users']['robot'] = User()
        root['users']['jane'] = User()
        self.request.root = root
        asd = IAuthSessionData(self.request)
        asd.new('robot', api_key = 'abc') #Will have id 1
        return root

    def test_remember(self):
        self._fixture()
        auth = self._cut()
        userid = 'jane'
        auth.remember(self.request, userid)
        self.assertEqual(userid, self.request.session['auth.userid'])
        self.assertEqual(auth.unauthenticated_userid(self.request), userid)

    def test_forget(self):
        self._fixture()
        auth = self._cut()
        userid = 'jane'
        self.request.session[auth.userid_key] = userid
        auth.forget(self.request)
        self.assertNotIn(userid, self.request.session)
        self.assertEqual(auth.unauthenticated_userid(self.request), None)

    def test_no_key(self):
        root = self._fixture()
        request = testing.DummyRequest()
        request.root = root
        obj = self._cut(callback = groupfinder)
        self.assertEqual(obj.authenticated_userid(request), None)
        request = testing.DummyRequest(params = {'key': '', 'userid': 'jane', 'session': '23'})
        request.root = root
        self.assertEqual(obj.authenticated_userid(request), None)

    def test_right_key(self):
        root = self._fixture()
        request = testing.DummyRequest(params = {'key': 'abc', 'userid': 'robot', 'session': '1'})
        request.root = root
        obj = self._cut(callback = groupfinder)
        self.assertEqual(obj.authenticated_userid(request), 'robot')

    def test_key_missmatch(self):
        root = self._fixture()
        request = testing.DummyRequest()
        request.root = root
        obj = self._cut(callback = groupfinder)
        self.assertEqual(obj.authenticated_userid(request), None)
        request = testing.DummyRequest(params = {'key': '123', 'userid': 'robot', 'session': '1'})
        request.root = root
        self.assertEqual(obj.authenticated_userid(request), None)

    def test_view_guard_allowed(self):
        from arche.views.base import BaseView
        from arche.views.base import APIKeyViewMixin
        class _ViewAllowed(BaseView, APIKeyViewMixin):
            pass

        self.config.set_authorization_policy(ACLAuthorizationPolicy())
        self.config.set_authentication_policy(self._cut())
        root = self._fixture()
        self.request.params = {'key': 'abc', 'userid': 'robot', 'session': '1'}
        self.request.root = root
        view = _ViewAllowed(root, self.request)
        self.assertEqual(view.request.authenticated_userid, 'robot')

    def test_view_guard_forbidden(self):
        from arche.views.base import BaseView
        class _ViewNotAllowed(BaseView):
            pass

        self.config.set_authorization_policy(ACLAuthorizationPolicy())
        self.config.set_authentication_policy(self._cut('secret'))
        root = self._fixture()
        self.request.root = root
        self.request.params = {'key': 'abc', 'userid': 'robot', 'session': '1'}
         #This must be touched to actually get a userid
        self.assertEqual(self.request.authenticated_userid, 'robot')
        self.assertRaises(HTTPForbidden, _ViewNotAllowed, root, self.request)


class AuthSessionDataTests(TestCase):

    def setUp(self):
        from arche.plugins.auth_sessions.models import ExtendedSessionAuthenticationPolicy
        from arche.security import groupfinder
        self.request = testing.DummyRequest(client_addr = '127.0.0.1', user_agent = 'Testing Browser')
        self.config = testing.setUp(request = self.request)
        self.config.set_authorization_policy(ACLAuthorizationPolicy())
        self.config.set_authentication_policy(ExtendedSessionAuthenticationPolicy(callback=groupfinder))

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.plugins.auth_sessions.models import AuthSessionData
        return AuthSessionData

    def _fixture(self):
        root = barebone_fixture(self.config)
        root['users']['robot'] = User()
        root['users']['jane'] = User()
        self.request.root = root
        return root

    def test_get_active(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'jane'
        self.assertEqual(ad, obj.get_active())

    def test_get_active_ip_locked(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane', ip_locked = ['192.168.0.1'])
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'jane'
        self.assertRaises(HTTPForbidden, obj.get_active)

    def test_get_all_active(self):
        self._fixture()
        obj = self._cut(self.request)
        obj.new('jane')
        obj.new('jane')
        obj.new('jane')
        self.assertEqual(len(obj.get_all_active('jane')), 3)

    def test_activity(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'jane'
        ad.last = older_timestamp = utcnow() - timedelta(days = 1)
        ad.max_valid = None
        obj.activity()
        self.assertNotEqual(ad.last, older_timestamp)

    def test_activity_expired(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'jane'
        ad.last = utcnow() - timedelta(days = 1)
        self.assertRaises(HTTPForbidden, obj.activity)

    def test_activity_useragent_missmatch(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'jane'
        ad.user_agent = "some other browser"
        self.assertRaises(HTTPForbidden, obj.activity)

    def test_activity_logout(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'other'
        self.assertRaises(HTTPForbidden, obj.activity)

    def test_new(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane', max_valid = 123)
        self.assertEqual(ad.max_valid, 123)

    def test_cleanup(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        ad.last = utcnow() - timedelta(days = 5)
        ad = obj.new('jane')
        ad.last = utcnow() - timedelta(days = 5)
        obj.max_keep_days = 1
        self.assertEqual(len(obj.sessions['jane']), 2)
        obj.cleanup('jane')
        self.assertEqual(len(obj.sessions['jane']), 0)

    def test_disable_inactive(self):
        self._fixture()
        obj = self._cut(self.request)
        for x in range(5):
            obj.new('jane')
        self.assertEqual(len(obj.get_all_active('jane')), 5)
        obj.max_sessions = 3
        obj.disable_inactive('jane')
        self.assertEqual(len(obj.get_all_active('jane')), 3)

    def test_close(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'jane'
        obj.close()
        self.failIf(ad.active)

    def test_close_logout(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.request.session['auth.session'] = 1
        self.request.session['auth.userid'] = 'jane'
        obj.close(logout=True)
        self.assertNotEqual(self.request.session.get('auth.session', None), 1)
        self.assertNotEqual(self.request.session.get('auth.userid', None), 'jane')

    def test_inactivate(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        obj.inactivate('jane', 1)
        self.failIf(ad.active)

    def test_get_data(self):
        self._fixture()
        obj = self._cut(self.request)
        ad = obj.new('jane')
        self.assertEqual(obj.get_data('jane')[0], ad)
