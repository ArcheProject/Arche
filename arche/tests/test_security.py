from unittest import TestCase

from pyramid import testing

from arche.testing import setup_auth
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
        self.config.include('arche.testing')
        self.config.include('arche.models.roles')
        self.config.include('arche.resources')
        self.config.include('arche.models.workflow')
        self.config.include('arche.models.acl')
        self.config.registry.acl['Root'] = 'private'
        root = root_populator(userid = 'admin')
        root['a'] = Document()
        a_roles = get_local_roles(root['a'])
        a_roles['tester'] = ['role:Administrator']
        root['b'] = Document()
        setup_auth(self.config, userid = 'tester', debug = False)
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

    def test_for_other_userid(self):
        root = self._fixture()
        request = testing.DummyRequest(context = root['a'])
        self.assertEqual(request.authenticated_userid, 'tester') #Just to make sure
        root['a'].local_roles['other'] = 'role:Administrator'
        self.failUnless(security.principal_has_permisson(request, 'other', security.PERM_EDIT, context=root['a']))
        self.failUnless(security.principal_has_permisson(request, 'tester', security.PERM_EDIT, context=root['a']))
        self.failIf(security.principal_has_permisson(request, 'xxx', security.PERM_EDIT, context=root))

    def test_context_effective_principals(self):
        root = self._fixture()
        request = testing.DummyRequest(context = root['a'])
        self.assertEqual(set(request.effective_principals),
                         set([security.ROLE_ADMIN, 'system.Everyone', 'system.Authenticated', 'tester']))
        self.assertEqual(set(security.context_effective_principals(request)),
                         set([security.ROLE_ADMIN, 'system.Everyone', 'system.Authenticated', 'tester']))
        self.assertEqual(set(security.context_effective_principals(request, root['a'])),
                         set([security.ROLE_ADMIN, 'system.Everyone', 'system.Authenticated', 'tester']))
        self.assertEqual(set(security.context_effective_principals(request, root['b'])),
                         set(['system.Everyone', 'system.Authenticated', 'tester']))

    def test_has_permission_other_userid(self):
        root = self._fixture()
        request = testing.DummyRequest(context = root['a'])
        self.failUnless(security.has_permission(request, security.PERM_EDIT))
        self.failUnless(security.has_permission(request, security.PERM_EDIT, root['a']))
        self.failIf(security.has_permission(request, security.PERM_EDIT, root))
        self.failIf(security.has_permission(request, security.PERM_EDIT, root['b']))


class GetRolesTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.models.acl')
        self.config.include('arche.models.roles')

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.security import get_roles
        return get_roles

    def _fixture(self):
        from arche.models.roles import Role
        #acl = self.config.registry.acl
        nothing = Role('role:nothing_set')
        inherit = Role('role:Inherit', inheritable = True)
        assignable = Role('role:Assignable', assignable = True)
        both = Role('role:Both', assignable = True, inheritable = True)
        self.config.register_roles(nothing, inherit, assignable, both)

    def test_get_roles(self):
        self._fixture()
        self.assertEqual(set(self._fut()), {'role:nothing_set', 'role:Inherit', 'role:Assignable', 'role:Both'})

    def test_get_roles_assignable(self):
        self._fixture()
        self.assertEqual(set(self._fut(assignable=True)), {'role:Assignable', 'role:Both'})
        self.assertEqual(set(self._fut(assignable=False)), {'role:nothing_set', 'role:Inherit'})

    def test_get_roles_inheritable(self):
        self._fixture()
        self.assertEqual(set(self._fut(inheritable=True)), {'role:Inherit', 'role:Both'})
        self.assertEqual(set(self._fut(inheritable=False)), {'role:nothing_set', 'role:Assignable'})

    def test_get_roles_both(self):
        self._fixture()
        self.assertEqual(list(self._fut(assignable=True, inheritable=True)), ['role:Both'])
        self.assertEqual(list(self._fut(assignable=False, inheritable=False)), ['role:nothing_set'])

#     def test_get_roles_assignable(self):
#         obj = self._cut()
#         one = self._acl()
#         _r_assignable = self._role('role:Hello', assignable = True)
#         one.add(_r_assignable, 'world')
#         obj['one'] = one
#         two = self._acl()
#         two.add('role:Something', 'else')
#         obj['two'] = two
#         self.assertEqual(obj.get_roles(assignable = True), set(['role:Hello']))
#         self.assertEqual(obj.get_roles(assignable = False), set(['role:Something']))
#         self.assertEqual(obj.get_roles(), set(['role:Hello', 'role:Something']))
# 
#     def test_get_roles_inheritable(self):
#         obj = self._cut()
#         one = self._acl()
#         _r_inheritable = self._role('role:Hello', inheritable = True)
#         one.add(_r_inheritable, 'world')
#         obj['one'] = one
#         two = self._acl()
#         two.add('role:Something', 'else')
#         obj['two'] = two
#         self.assertEqual(obj.get_roles(inheritable = True), set(['role:Hello']))
#         self.assertEqual(obj.get_roles(inheritable = False), set(['role:Something']))
#         self.assertEqual(obj.get_roles(), set(['role:Hello', 'role:Something']))