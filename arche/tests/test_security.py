from unittest import TestCase

from pyramid import testing
from pyramid.request import Request

from arche.testing import setup_security
from arche import security


class ContextPermIntegrationTests(TestCase):
    
    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    def _fixture(self):
        from arche.populators import root_populator
        from arche.resources import Document
        from arche.security import get_local_roles
        self.config.include('arche.utils')
        self.config.include('arche.security')
        self.config.include('arche.resources')
        setup_security(self.config, userid = 'tester', debug = False)
        root = root_populator(userid = 'admin')
        root['a'] = Document()
        a_roles = get_local_roles(root['a'])
        a_roles['tester'] = ['role:Administrator']
        root['b'] = Document()
        return root

    def test_effective_principals(self):
        root = self._fixture()
        request = testing.DummyRequest(context = root['a'])
        self.assertEqual(set(request.effective_principals), set([security.ROLE_ADMIN, 'system.Everyone', 'system.Authenticated', 'tester']))
        request = testing.DummyRequest(context = root['b'])
        self.assertEqual(set(request.effective_principals), set(['system.Everyone', 'system.Authenticated', 'tester']))
 
    def test_groupfinder(self):
        root = self._fixture()
        request = testing.DummyRequest(context = root['a'])
        from arche.security import groupfinder
        self.assertEqual(groupfinder(None, request), ())
        self.assertEqual(groupfinder('tester', request), set([security.ROLE_ADMIN]))
        self.assertEqual(groupfinder('admin', request), set([security.ROLE_ADMIN, 'group:administrators']))

    def test_request_context_not_used_for_another_context(self):        
        root = self._fixture()
        request = testing.DummyRequest(context = root['a'])
        self.assertEqual(request.authenticated_userid, 'tester') #Just to make sure
        self.failUnless(security.has_permission(request, security.PERM_EDIT))
        self.failUnless(security.has_permission(request, security.PERM_EDIT, root['a']))
        self.failIf(security.has_permission(request, security.PERM_EDIT, root))
        self.failIf(security.has_permission(request, security.PERM_EDIT, root['b']))
