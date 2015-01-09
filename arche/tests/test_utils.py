# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from pyramid import testing


def _dummy_view(*args):
    return {}


class GetViewTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.utils import get_view
        return get_view

    def _fixture(self, name = ''):
        self.config.add_view(_dummy_view, context=testing.DummyResource, name = name)

    def test_no_view(self):
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.assertEqual(self._fut(context, request), None)

    def test_default_view(self):
        self._fixture()
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.failUnless(self._fut(context, request))

    def test_named_view(self):
        self._fixture(name = 'hello')
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.failUnless(self._fut(context, request, view_name = 'hello'))


class GenerateSlugTests(TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.utils import generate_slug
        return generate_slug

    def test_chineese(self):
        context = testing.DummyResource()
        hello = "您好"
        self.assertEqual(self._fut(context, hello), "nin-hao")

    def test_ukranian(self):
        context = testing.DummyResource()
        hello = "Привіт"
        self.assertEqual(self._fut(context, hello), "privit")

    def test_swedish(self):
        context = testing.DummyResource()
        text = "Héj åäö"
        self.assertEqual(self._fut(context, text), "hej-aao")

    def test_registered_views(self):
        self.config.add_view(_dummy_view, name = 'dummy', context = testing.DummyResource)
        context = testing.DummyResource()
        self.assertEqual(self._fut(context, 'dummy'), "dummy-1")

    def test_with_existing_keys(self):
        context = testing.DummyResource()
        context['hello'] = testing.DummyResource()
        self.assertEqual(self._fut(context, 'hello'), "hello-1")
