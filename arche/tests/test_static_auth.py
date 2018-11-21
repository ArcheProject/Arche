from unittest import TestCase

from pyramid import testing
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.interfaces import IAuthenticationPolicy
from zope.interface.verify import verifyObject


class StaticAuthenticationPolicyTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.scripting import StaticAuthenticationPolicy
        return StaticAuthenticationPolicy

    def test_interface(self):
        self.failUnless(verifyObject(IAuthenticationPolicy, self._cut()))

    def test_integration(self):
        self.config.set_authorization_policy(ACLAuthorizationPolicy())
        authn = self._cut()
        self.config.set_authentication_policy(authn)
        request = testing.DummyRequest()
        authn.remember(request, 'jane')
        self.assertEqual(request.authenticated_userid, 'jane')
