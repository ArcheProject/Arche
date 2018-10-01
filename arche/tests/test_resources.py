from __future__ import unicode_literals

from unittest import TestCase

from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.interfaces import IBase
from arche.interfaces import IUser
from arche.interfaces import IUsers
from arche.interfaces import IToken
from arche.interfaces import IContextACL
from arche.testing import barebone_fixture
from arche.interfaces import IEmailValidatedEvent


class BaseTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.resources import Base
        return Base

    def test_verify_class(self):
        verifyClass(IBase, self._cut)

    def test_verify_object(self):
        verifyObject(IBase, self._cut())


class UsersTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.api import Users
        return Users

    @property
    def _User(self):
        from arche.api import User
        return User

    def test_verify_class(self):
        verifyClass(IUsers, self._cut)

    def test_verify_object(self):
        verifyObject(IUsers, self._cut())

    def _fixture(self):
        self.config.include('arche.testing')
        self.config.include('arche.models.catalog')
        return barebone_fixture(self.config)

    def test_get_user_by_email(self):
        root = self._fixture()
        obj = root['users']
        obj['one'] = self._User(email = 'jane@archeproject.org')
        self.assertTrue(obj.get_user_by_email('jane@archeproject.org'))
        self.assertTrue(obj.get_user_by_email('JANE@archeproject.org'))

    def test_get_user_by_email_2_results_error(self):
        root = self._fixture()
        obj = root['users']
        obj['one'] = self._User(email = 'jane@archeproject.org')
        obj['two'] = self._User(email = 'jane@archeproject.org')
        self.assertRaises(ValueError, obj.get_user_by_email, 'jane@archeproject.org')

    def test_get_user_by_email_no_result(self):
        root = self._fixture()
        obj = root['users']
        _marker = object()
        self.assertEqual(obj.get_user_by_email('JANE@archeproject.org', _marker), _marker)

    def test_get_user_by_email_only_validated(self):
        root = self._fixture()
        obj = root['users']
        _marker = object()
        obj['jane'] = user = self._User(email = 'jane@archeproject.org')
        self.assertEqual(obj.get_user_by_email('jane@archeproject.org', _marker, only_validated = True), _marker)
        self.assertEqual(obj.get_user_by_email('jane@archeproject.org', _marker, only_validated = False), user)
        user.email_validated = True
        self.assertEqual(obj.get_user_by_email('jane@archeproject.org', _marker, only_validated = True), user)


class UserTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.api import User
        return User

    def test_verify_class(self):
        verifyClass(IUser, self._cut)

    def test_verify_object(self):
        verifyObject(IUser, self._cut())

    def _fixture(self):
        self.config.include('arche.testing')
        self.config.include('arche.models.catalog')
        self.config.include('arche.subscribers')
        return barebone_fixture(self.config)

    def _subsc(self):
        L = []
        def subscriber(event):
            L.append(event.user)
        self.config.add_subscriber(subscriber, IEmailValidatedEvent)
        return L

    def test_email_event_fires_on_attach(self):
        L = self._subsc()
        root = self._fixture()
        user = self._cut(email_validated = True, email = "hello@betahaus.net")
        self.assertFalse(L)
        root['users']['user'] = user
        self.assertIn(user, L)

    def test_email_event_fires_when_changed(self):
        L = self._subsc()
        root = self._fixture()
        root['users']['user'] = user = self._cut(email = "hello@betahaus.net")
        self.assertFalse(L)
        user.email_validated = True
        self.assertEqual(len(L), 1)
        user.email_validated = True
        self.assertEqual(len(L), 1)


def _attach_dummy_acl(config, name = 'default', role = 'role:Dummy'):
    aclreg = config.registry.acl
    aclreg.pop(name, None)
    new_acl = aclreg.new_acl(name)
    new_acl.add(role, 'Do Stuff')
    return new_acl


class ContextACLTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.testing')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.api import ContextACLMixin
        return ContextACLMixin

    def _mk_dummy(self):
        class _Dummy(testing.DummyResource, self._cut):
            type_name = 'Dummy'
        return _Dummy()

    def test_verify_class(self):
        self.failUnless(verifyClass(IContextACL, self._cut))

    def test_verify_obj(self):
        #We need to add an acl here since the interface test won't like the raised attribute error
        self.config.registry.acl.new_acl('Dummy')
        self.failUnless(verifyObject(IContextACL, self._mk_dummy()))

    def test_default_if_nothing_else(self):
        context = self._mk_dummy()
        _attach_dummy_acl(self.config)
        self.assertEqual(context.__acl__[0], ('Allow', 'role:Dummy', set(['Do Stuff'])))

    def test_type_name_same_as_acl(self):
        context = self._mk_dummy()
        _attach_dummy_acl(self.config, name = 'Dummy', role = 'role:HiDummy')
        #Since the name matches
        self.assertEqual(context.__acl__[0], ('Allow', 'role:HiDummy', set(['Do Stuff'])))

    def test_set_wf_precedence(self):
        self.config.include('arche.models.workflow')
        context = self._mk_dummy()
        _attach_dummy_acl(self.config)
        _attach_dummy_acl(self.config, name = 'Dummy')
        self.config.set_content_workflow('Dummy', 'simple_workflow')
        # A bit too specific but at least not the same as other set workflows
        # FIXME Robin: py3(only?) gives 'role:Administrator'
        self.assertEqual(context.__acl__[0][0:2], ('Allow', 'role:Owner',))


class TokenTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.resources import Token
        return Token

    def test_verify_class(self):
        verifyClass(IToken, self._cut)

    def test_verify_object(self):
        verifyObject(IToken, self._cut())

    def test_eq(self):
        obj1 = self._cut()
        obj2 = self._cut()
        self.assertNotEqual(obj1, obj2)
        obj2.token = obj1.token = '1'
        self.assertEqual(obj1, obj2)
        self.assertEqual(obj1, '1')
        self.assertTrue(obj1 == '1')

    def test_ne(self):
        obj1 = self._cut()
        obj2 = self._cut()
        self.assertNotEqual(obj1, obj2)
        obj2.token = obj1.token = '1'
        self.assertEqual(obj1, obj2)
        self.assertNotEqual(obj1, '2')
        self.assertFalse(obj1 != '1')
        self.assertTrue(obj1 != '2')
