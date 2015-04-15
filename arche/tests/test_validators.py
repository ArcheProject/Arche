# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

from pyramid import testing
from colander import Invalid

from arche.testing import barebone_fixture


class NewUserIDValidatorTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import NewUserIDValidator
        return NewUserIDValidator

    def _fixture(self):
        root = barebone_fixture(self.config)
        request = testing.DummyRequest()
        return root['users'], request

    def test_supposed_pass(self):
        obj = self._cut(*self._fixture())
        self.assertEqual(obj(None, 'arche'), None)

    def test_uppercase(self):
        obj = self._cut(*self._fixture())
        self.assertRaises(Invalid, obj, None, 'Arche')

    def text_int_chars(self):
        obj = self._cut(*self._fixture())
        self.assertRaises(Invalid, obj, None, 'ärche')

    def test_view_name(self):
        def view(*args):
            pass
        self.config.add_view(view, name = 'arche')
        obj = self._cut(*self._fixture())
        self.assertRaises(Invalid, obj, None, 'arche')

    def test_system_like_name(self):
        obj = self._cut(*self._fixture())
        self.assertRaises(Invalid, obj, None, 'role:hi')
        self.assertRaises(Invalid, obj, None, '_something')

    def test_too_long(self):
        obj = self._cut(*self._fixture())
        name = "".join(['x' for x in range(30)])
        self.assertEqual(obj(None, name), None)
        name += 'x'
        self.assertRaises(Invalid, obj, None, name)


class UniqueEmailTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.testing')
        self.config.include('arche.models.catalog')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import UniqueEmail
        return UniqueEmail

    @property
    def _User(self):
        from arche.api import User
        return User

    def test_email_in_empty_site(self):
        root = barebone_fixture(self.config)
        obj = self._cut(root)
        self.assertFalse(obj(None, 'some@email.com'))

    def test_email_exists_root(self):
        root = barebone_fixture(self.config)
        root['users']['one'] = self._User(email = 'some@email.com')
        obj = self._cut(root)
        self.assertRaises(Invalid, obj, None, 'some@email.com')

    def test_email_exists_user_context(self):
        root = barebone_fixture(self.config)
        root['users']['one'] = self._User(email = 'some@email.com')
        root['users']['two'] = self._User(email = 'other@email.com')
        obj = self._cut(root['users']['two'])
        self.assertRaises(Invalid, obj, None, 'some@email.com')

    def test_email_exists_but_is_own_profile(self):
        root = barebone_fixture(self.config)
        root['users']['one'] = self._User(email = 'some@email.com')
        obj = self._cut(root['users']['one'])
        self.assertFalse(obj(None, 'some@email.com'))


class ExistingUserIDsTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import ExistingUserIDs
        return ExistingUserIDs

    def _fixture(self):
        root = barebone_fixture(self.config)
        return root['users']

    def test_supposed_pass(self):
        users = self._fixture()
        users['userid'] =  testing.DummyResource()
        obj = self._cut(users)
        self.assertEqual(obj(None, 'userid'), None)

    def test_supposed_fail(self):
        users = self._fixture()
        obj = self._cut(users)
        self.assertRaises(Invalid, obj, None, 'userid')

    def test_supposed_pass_list(self):
        users = self._fixture()
        users['arche'] =  testing.DummyResource()
        users['jane'] =  testing.DummyResource()
        obj = self._cut(users)
        self.assertEqual(obj(None, ['jane', 'arche']), None)
