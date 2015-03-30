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
        #Note. populators will probably change
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