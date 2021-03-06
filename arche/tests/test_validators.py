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


class AllowUserLoginValidatorTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import AllowUserLoginValidator
        return AllowUserLoginValidator

    def _fixture(self, **kw):
        from arche.api import User
        root = barebone_fixture(self.config)
        root['users']['user'] = User(**kw)
        return root

    def test_allowed_userid(self):
        root = self._fixture()
        obj = self._cut(root)
        self.assertFalse(obj(None, 'user'))

    def test_not_allowed_userid(self):
        root = self._fixture(allow_login = False)
        obj = self._cut(root)
        self.assertRaises(Invalid, obj, None, 'user')

    def test_nonexistent_userid(self):
        root = self._fixture()
        obj = self._cut(root)
        self.assertRaises(Invalid, obj, None, '404')

    def test_nonexistent_email(self):
        root = self._fixture()
        obj = self._cut(root)
        self.assertRaises(Invalid, obj, None, '404@betahaus.net')

    def test_allowed_email(self):
        root = self._fixture(email = 'found@betahaus.net')
        obj = self._cut(root)
        self.assertFalse(obj(None, 'found@betahaus.net'))


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


class ExistingUserIDOrEmailTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import ExistingUserIDOrEmail
        return ExistingUserIDOrEmail

    def _fixture(self):
        root = barebone_fixture(self.config)
        return root['users']

    def test_supposed_pass_userid(self):
        users = self._fixture()
        users['userid'] = testing.DummyResource()
        obj = self._cut(users)
        self.assertEqual(obj(None, 'userid'), None)

    def test_supposed_fail_userid(self):
        users = self._fixture()
        obj = self._cut(users)
        self.assertRaises(Invalid, obj, None, 'userid')

    def test_supposed_pass_email(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        from arche.api import User
        users = self._fixture()
        users['userid'] = user = User(email = 'tester@archeproject.org')
        obj = self._cut(users)
        self.assertEqual(obj(None, 'tester@archeproject.org'), None)

    def test_supposed_fail_email(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        from arche.api import User
        users = self._fixture()
        users['userid'] = user = User(email = 'tester@archeproject.org')
        obj = self._cut(users)
        self.assertRaises(Invalid, obj, None, 'no_one@archeproject.org')
        self.assertRaises(Invalid, obj, None, 'hello @ jeff')
        self.assertRaises(Invalid, obj, None, 'åäö@archeproject.org')


class ExistingPathValidatorTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import ExistingPathValidator
        return ExistingPathValidator

    def test_404(self):
        root = testing.DummyResource()
        obj = self._cut(None, {'context': root})
        self.assertRaises(Invalid, obj, None, '/hello404')

    def test_root(self):
        root = testing.DummyResource()
        obj = self._cut(None, {'context': root})
        obj(None, '')
        obj(None, '/')

    def test_existing_path(self):
        root = testing.DummyResource()
        root['mystuff'] = testing.DummyResource()
        obj = self._cut(None, {'context': root})
        obj(None, 'mystuff')
        obj(None, '/mystuff')
        obj(None, '/mystuff/')



class URLOrExistingPathValidatorTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import URLOrExistingPathValidator
        return URLOrExistingPathValidator

    def test_404(self):
        root = testing.DummyResource()
        obj = self._cut(None, {'context': root})
        self.assertRaises(Invalid, obj, None, '/hello404')

    def test_root(self):
        root = testing.DummyResource()
        obj = self._cut(None, {'context': root})
        obj(None, '/')

    def test_url(self):
        root = testing.DummyResource()
        obj = self._cut(None, {'context': root})
        obj(None, 'http://www.betahaus.net')



class ShortNameValidatorTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.validators import ShortNameValidator
        return ShortNameValidator

    def test_traversal_object(self):
        root = testing.DummyResource()
        root['hello'] = testing.DummyResource()
        request = testing.DummyRequest()
        obj = self._cut(None, {'context': root, 'request': request})
        self.assertRaises(Invalid, obj, None, 'hello')

    def test_traversal_view(self):
        def _dummy(*args):
            pass
        self.config.add_view(_dummy, name='a_view', context = testing.DummyResource)
        root = testing.DummyResource()
        request = testing.DummyRequest()
        obj = self._cut(None, {'context': root, 'request': request})
        self.assertRaises(Invalid, obj, None, 'a_view')

    def test_ok(self):
        root = testing.DummyResource()
        root['hello'] = testing.DummyResource()
        request = testing.DummyRequest()
        obj = self._cut(None, {'context': root, 'request': request})
        obj(None, 'world')
