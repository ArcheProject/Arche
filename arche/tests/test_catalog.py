from unittest import TestCase

from pyramid import testing
from zope.interface import implementer

from arche.interfaces import ICataloger
from arche.interfaces import IIndexedContent


def _dummy_func(*args):
    return args


class CatalogIntegrationTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.catalog')
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.catalog import Cataloger
        return Cataloger

    def _fixture(self):
        from arche.resources import Root
        return Root()

    def _mk_context(self):
        from arche.resources import Base
        @implementer(IIndexedContent)
        class _DummyIndexedContent(Base):
            title = u"hello"
            description = u"world"
        return _DummyIndexedContent()

    def test_init_on_adapt(self):
        root = self._fixture()
        self._cut(root)
        self.assertIn('title', root.catalog)

    def test_index_object(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        obj.index_object()
        self.assertIn('/a', obj.document_map.address_to_docid)

    def test_unindex_object(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        obj.index_object()
        self.assertIn('/a', obj.document_map.address_to_docid)
        obj.unindex_object()
        self.assertNotIn('/a', obj.document_map.address_to_docid)

    def test_title_index(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("title == 'hello'")
        self.assertEqual(res[0], 1)

    def test_uid_index(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("uid == '%s'" % context.uid)
        self.assertEqual(res[0], 1)

    def test_searchable_text(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("searchable_text == 'hello'")
        self.assertEqual(res[0], 1)
        res = obj.catalog.query("searchable_text == 'hel*'")
        self.assertEqual(res[0], 1)
        res = obj.catalog.query("searchable_text == 'world'")
        self.assertEqual(res[0], 1)

    def test_subscribers(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        res = obj.catalog.query("title == 'hello'")
        self.assertEqual(res[0], 1)
        del root['a']
        res = obj.catalog.query("title == 'hello'")
        self.assertEqual(res[0], 0)

    def test_changed_subscriber(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        res = obj.catalog.query("title == 'hello'")
        self.assertEqual(res[0], 1)
        context.update(title = u'something')
        self.assertEqual(context.title, 'something') #Just to make sure the tests isn't wrong
        res = obj.catalog.query("title == 'hello'")
        self.assertEqual(res[0], 0)
        res = obj.catalog.query("title == 'something'")
        self.assertEqual(res[0], 1)
