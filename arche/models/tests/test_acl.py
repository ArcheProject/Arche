from unittest import TestCase

from pyramid import testing
from pyramid.security import ALL_PERMISSIONS, DENY_ALL


class ACLEntryTests(TestCase):    
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.acl import ACLEntry
        return ACLEntry

    def test_add_string(self):
        obj = self._cut()
        obj.add('role:Admin', 'Hello perm')
        self.assertEqual(obj()[0], ('Allow', 'role:Admin', set(['Hello perm'])))

    def test_add_tuple(self):
        obj = self._cut()
        obj.add('role:Admin', ('perm:Show', 'View'))
        self.assertEqual(obj()[0], ('Allow', 'role:Admin', set(['perm:Show', 'View'])))

    def test_add_combined(self):
        obj = self._cut()
        obj.add('role:Admin', ('One', 'Three'))
        obj.add('role:Admin', 'Two')
        obj.add('role:Other', 'One')
        self.assertEqual(obj()[:-1], [('Allow', 'role:Admin', set(['Two', 'Three', 'One'])), ('Allow', 'role:Other', set(['One']))])

    def test_remove(self):
        obj = self._cut()
        obj.add('role:Admin', ('One', 'Three'))
        obj.add('role:Admin', 'Two')
        obj.add('role:Other', 'One')
        obj.remove('role:Admin', 'Two')
        obj.remove('role:Other', 'One')
        self.assertEqual(obj()[:-1], [('Allow', 'role:Admin', set(['Three', 'One'])), ('Allow', 'role:Other', set([]))])

    def test_remove_all_perms_object(self):
        obj = self._cut()
        obj.add('role:Admin', ('One', 'Three'))
        self.assertEqual(len(obj()), 2)
        obj.remove('role:Admin', ALL_PERMISSIONS)
        self.assertEqual(len(obj()), 1)



class ACLRegistryTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.acl import ACLRegistry
        return ACLRegistry

    @property
    def _acl(self):
        from arche.models.acl import ACLEntry
        return ACLEntry

    @property
    def _role(self):
        from arche.models.roles import Role
        return Role

    def test_linking(self):
        obj = self._cut()
        one = self._acl()
        one.add('role:Hello', 'world')
        obj['one'] = one
        obj['link'] = 'one'
        self.assertTrue(obj.is_linked('link'))
        self.assertFalse(obj.is_linked('one'))
        self.assertEqual(obj.get_acl('link'), obj.get_acl('one'))
        
    def test_linking_to_nonexistent(self):
        obj = self._cut()
        try:
            obj['dummy'] = ''
        except ValueError:
            pass

    def test_setting_bad_obj(self):
        obj = self._cut()
        try:
            obj['dummy'] = object()
        except TypeError:
            pass

    def test_get_acl(self):
        obj = self._cut()
        one = self._acl()
        one.add('role:Hello', 'world')
        obj['one'] = one
        self.assertEqual(obj.get_acl('one'), [('Allow', 'role:Hello', set(['world'])), DENY_ALL,])
