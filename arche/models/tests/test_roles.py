from unittest import TestCase

from pyramid import testing
from zope.interface import implementer
#from pyramid.security import ALL_PERMISSIONS, DENY_ALL

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

    def test_includes(self):
        role_one = self._role('role:one')
        role_two = self._role('role:two', includes = 'role:one')
        obj = self._cut(_DummyContent())
        obj['jane'] = role_two
        self.assertEqual(obj['jane'], frozenset(['role:one', 'role:two']))
