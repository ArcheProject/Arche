from unittest import TestCase

from pyramid import testing
from zope.interface import implementer

from arche.interfaces import IContent
from arche.resources import LocalRolesMixin


@implementer(IContent)
class _DummyContent(testing.DummyResource, LocalRolesMixin):
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
