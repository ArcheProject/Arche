from unittest import TestCase

from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
from pyramid.authorization import ACLAuthorizationPolicy

from arche.security import groupfinder
from arche.testing import barebone_fixture
from arche.api import User


class KeyAndTktAuthenticationTests(TestCase):
    
    def setUp(self):
        self.request = testing.DummyRequest()
        self.config = testing.setUp(request = self.request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.authentication import KeyAndTktAuthentication
        return KeyAndTktAuthentication

    def _fixture(self):
        root = barebone_fixture(self.config)
        root['users']['robot'] = User(apikey = 'abc')
        root['users']['jane'] = User()
        return root

    def test_no_key(self):
        root = self._fixture()
        request = testing.DummyRequest()
        request.root = root
        obj = self._cut(secret = 'xyz', callback = groupfinder, hashalg = 'sha512')
        self.assertEqual(obj.authenticated_userid(request), None)
        request = testing.DummyRequest(params = {'apikey': '', 'userid': 'jane'})
        request.root = root
        self.assertEqual(obj.authenticated_userid(request), None)

    def test_right_key(self):
        root = self._fixture()
        request = testing.DummyRequest(params = {'apikey': 'abc', 'userid': 'robot'})
        request.root = root
        obj = self._cut(secret = 'xyz', callback = groupfinder, hashalg = 'sha512')
        self.assertEqual(obj.authenticated_userid(request), 'robot')

    def test_view_guard_allowed(self):
        from arche.views.base import BaseView
        from arche.views.base import APIKeyViewMixin
        class _ViewAllowed(BaseView, APIKeyViewMixin):
            pass

        self.config.include('arche.models.authentication')
        self.config.set_authorization_policy(ACLAuthorizationPolicy())
        self.config.set_authentication_policy(self._cut('secret'))
        root = self._fixture()
        self.request.params = {'apikey': 'abc', 'userid': 'robot'}
        self.request.root = root
        view = _ViewAllowed(root, self.request)
        self.assertEqual(view.request.authenticated_userid, 'robot')

    def test_view_guard_forbidden(self):
        from arche.views.base import BaseView
        class _ViewNotAllowed(BaseView):
            pass

        self.config.include('arche.models.authentication')
        self.config.set_authorization_policy(ACLAuthorizationPolicy())
        self.config.set_authentication_policy(self._cut('secret'))
        root = self._fixture()
        self.request.root = root
        self.request.params = {'apikey': 'abc', 'userid': 'robot'}
        self.request.authenticated_userid #This must be touched to actually get a userid
        self.assertRaises(HTTPForbidden, _ViewNotAllowed, root, self.request)
