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
        self.config.add_view(_dummy_view, context=testing.DummyResource, name= '')

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
        self._fixture()
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.failUnless(self._fut(context, request))
