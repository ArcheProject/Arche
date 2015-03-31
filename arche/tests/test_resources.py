from unittest import TestCase

from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.interfaces import IBase
from arche.interfaces import IUsers
from arche.interfaces import IToken
from arche.testing import barebone_fixture


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
