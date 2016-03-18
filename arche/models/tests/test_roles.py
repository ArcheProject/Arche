from unittest import TestCase

from pyramid import testing
from zope.interface import implementer
from zope.interface import Interface
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.interfaces import IContent
from arche.interfaces import IRoles
from arche.resources import LocalRolesMixin


@implementer(IContent)
class _DummyContent(testing.DummyResource, LocalRolesMixin):
    pass


class IOther(Interface):
    pass


class RolesTests(TestCase):    
    
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.security')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.roles import Roles
        return Roles

    @property
    def _role(self):
        from arche.models.roles import Role
        return Role

    def test_verify_class(self):
        self.failUnless(verifyClass(IRoles, self._cut))

    def test_verify_obj(self):
        context = _DummyContent()
        obj = self._cut(context)
        self.failUnless(verifyObject(IRoles, obj))

    def test_assign_string(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['hello'] = 'world'
        self.assertIn('world', obj['hello'])

    def test_assign_role(self):
        context = _DummyContent()
        obj = self._cut(context)
        role = self._role('role:World')
        obj['hello'] = role
        self.assertIn(role, obj['hello'])

    def test_assign_list(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['hello'] = ['one', 'two']
        self.assertEqual(obj['hello'], set(['one', 'two']))

    def test_assign_other_context(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['hello'] = ['one', 'two']
        other = _DummyContent()
        obj2 = self._cut(other)
        obj2.set_from_appstruct(obj)
        self.assertEqual(dict(obj), dict(obj2))

    def test_assigning_none_clears(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['hello'] = ['one', 'two']
        self.assertIn('hello', obj)
        obj['hello'] = None
        self.assertNotIn('hello', obj)

    def test_update(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['hello'] = ['one', 'two']
        other = _DummyContent()
        obj2 = self._cut(other)
        obj2['hello'] = 'three'
        obj.update(obj2)
        self.assertEqual(obj['hello'], frozenset(['three']))

    def test_add(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['hello'] = ['one', 'two']
        obj.add('hello', 'three')
        self.assertEqual(obj['hello'], frozenset(['one', 'two', 'three']))
        obj.add('hello', ['four'])
        self.assertEqual(obj['hello'], frozenset(['one', 'two', 'three', 'four']))

    def test_remove(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['hello'] = ['one', 'two', 'three', 'four']
        obj.remove('hello', 'four')
        self.assertEqual(obj['hello'], frozenset(['one', 'two', 'three']))
        obj.remove('hello', ['three', 'two'])
        self.assertEqual(obj['hello'], frozenset(['one']))
        obj.remove('hello', 'one')
        self.assertNotIn('hello', obj)

    def test_get_any_local_with(self):
        context = _DummyContent()
        obj = self._cut(context)
        obj['first'] = ['one', 'two', 'three', 'four']
        obj['second'] = ['one', 'two', 'three']
        obj['third'] = ['three']
        self.assertEqual(set(obj.get_any_local_with('one')), set(['first', 'second']))
        self.assertEqual(set(obj.get_any_local_with('three')), set(['first', 'second', 'third']))

    def test_get_assignable(self):
        role_global = self._role('role:Global', assignable=True)
        role_non_assignable = self._role('role:Non', assignable=False)
        role_content = self._role('role:Content', required=IContent, assignable=True)
        role_other = self._role('role:Other', required=IOther, assignable=True)
        self.config.register_roles(role_global, role_non_assignable, role_content, role_other)
        context = _DummyContent()
        obj = self._cut(context)
        result = set(obj.get_assignable())
        self.assertIn(role_global, result)
        self.assertNotIn(role_non_assignable, result)
        self.assertIn(role_content, result)
        self.assertNotIn(role_other, result)
