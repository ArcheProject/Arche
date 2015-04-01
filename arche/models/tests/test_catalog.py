from unittest import TestCase

from pyramid import testing
from zope.interface import implementer
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from zope.component import adapter
from repoze.catalog.indexes.field import CatalogFieldIndex

from arche.interfaces import ICataloger, IMetadata
from arche.interfaces import IIndexedContent
from arche.exceptions import CatalogError
from zope.interface.exceptions import BrokenMethodImplementation


def _dummy_func(*args):
    return args

def _wf_fixture(config):
    from arche.resources import ContextACLMixin

    @implementer(IIndexedContent)
    class Dummy(testing.DummyResource, ContextACLMixin):
        type_name = 'Dummy'

    config.include('arche.utils')
    config.include('arche.security')
    config.include('arche.models.workflow')
    config.set_content_workflow('Dummy', 'simple_workflow')
    return Dummy()


class CatalogIntegrationTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.models.catalog')
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.catalog import Cataloger
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
            type_name = 'Dummy'
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

    def test_searchable_text_add_field(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("searchable_text == 'Dummy'")
        self.assertEqual(res[0], 0)
        self.config.add_searchable_text_index('type_name')
        obj.index_object()
        res = obj.catalog.query("searchable_text == 'Dummy'")
        self.assertEqual(res[0], 1)

    def test_searchable_text_add_discriminator(self):
        root = self._fixture()
        root['a'] = context = self._mk_context()
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("searchable_text == 'Dummy'")
        self.assertEqual(res[0], 0)
        def _dummy(context, default):
            return 'Dummy'
        self.config.add_searchable_text_discriminator(_dummy)
        obj.index_object()
        res = obj.catalog.query("searchable_text == 'Dummy'")
        self.assertEqual(res[0], 1)

    def test_wf_state_index(self):
        root = self._fixture()
        root['a'] = context = _wf_fixture(self.config)
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("wf_state == 'private'")
        self.assertEqual(res[0], 1)

    def test_workflow_index(self):
        root = self._fixture()
        root['a'] = context = _wf_fixture(self.config)
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("workflow == 'simple_workflow'")
        self.assertEqual(res[0], 1)

    def test_workflow_subscriber(self):
        from arche.models.workflow import get_context_wf

        root = self._fixture()
        root['a'] = context = _wf_fixture(self.config)
        obj = self._cut(context)
        obj.index_object()
        res = obj.catalog.query("wf_state == 'private'")
        self.assertEqual(res[0], 1)

        request = testing.DummyRequest()
        wf = get_context_wf(context)
        wf.do_transition('private:public', request)
        res = obj.catalog.query("wf_state == 'private'")
        self.assertEqual(res[0], 0)
        res = obj.catalog.query("wf_state == 'public'")
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


class MetadataTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.catalog import Metadata
        return Metadata
# 
    def _mk_context(self):
        from arche.resources import Base
        @implementer(IIndexedContent)
        class _DummyIndexedContent(Base):
            title = u"hello"
            description = u"world"
        return _DummyIndexedContent()

    @property
    def _dummy_metadata(self):
        @adapter(IIndexedContent)
        class _DummyMetadata(self._cut):
            name = 'dummy'
            def __call__(self, default = None):
                return "Hello"
        return _DummyMetadata

    def test_verify_class(self):
        self.failUnless(verifyClass(IMetadata, self._cut))

    def test_verify_object(self):
        obj = self._cut(testing.DummyResource())
        self.failUnless(verifyObject(IMetadata, obj))

    def test_integration_add(self):
        self.config.include('arche.models.catalog')
        self.config.add_metadata_field(self._dummy_metadata)
        context = self._mk_context()
        self.failUnless(self.config.registry.queryAdapter(context, IMetadata, name = 'dummy'))

    def test_integration_get_metadata(self):
        self.config.include('arche.models.catalog')
        self.config.add_metadata_field(self._dummy_metadata)
        from arche.api import Root
        root = Root()
        root['c'] = context = self._mk_context()
        cataloger = ICataloger(context)
        self.assertEqual(cataloger.get_metadata(), {'dummy': 'Hello'})

    def test_metadata_added_on_index(self):
        self.config.include('arche.models.catalog')
        self.config.add_metadata_field(self._dummy_metadata)
        from arche.api import Root
        root = Root()
        cataloger = ICataloger(root)
        cataloger.index_object()
        self.assertEqual(len(root.document_map.docid_to_metadata), 1)
        for v in root.document_map.docid_to_metadata.values():
            result = dict(v)
        self.assertEqual(result, {'dummy': 'Hello'})

    def test_integration_create_metadata_field(self):
        self.config.include('arche.models.catalog')
        def _callable(self, default = None):
            return 'Hello world'
        self.config.create_metadata_field(_callable, 'dummy')
        from arche.api import Root
        root = Root()
        cataloger = ICataloger(root)
        cataloger.index_object()
        self.assertEqual(len(root.document_map.docid_to_metadata), 1)
        for v in root.document_map.docid_to_metadata.values():
            result = dict(v)
        self.assertEqual(result, {'dummy': 'Hello world'})

    def test_integration_create_metadata_field_bad_callable(self):
        self.config.include('arche.models.catalog')
        def _callable():
            return 'Hello world'
        self.assertRaises(BrokenMethodImplementation, self.config.create_metadata_field, _callable, 'dummy')

    def test_integration_create_metadata_field_attribute(self):
        self.config.include('arche.models.catalog')
        self.config.create_metadata_field('title', 'dummy')
        from arche.api import Root
        root = Root(title = 'Hello world')
        cataloger = ICataloger(root)
        cataloger.index_object()
        self.assertEqual(len(root.document_map.docid_to_metadata), 1)
        for v in root.document_map.docid_to_metadata.values():
            result = dict(v)
        self.assertEqual(result, {'dummy': 'Hello world'})


class CheckCatalogOnStartupTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.models.catalog')
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.models.catalog import check_catalog_on_startup
        return check_catalog_on_startup

    def _fixture(self):
        from arche.api import Root
        return {'closer': object, 'root': Root(), 'registry': self.config.registry}

    def test_check_catalog_on_startup(self):
        env = self._fixture()
        self._fut(env = env)

    def test_check_detects_missing(self):
        env = self._fixture()
        del env['root'].catalog['title']
        self.assertRaises(CatalogError, self._fut, env = env)

    def test_check_detects_too_many(self):
        env = self._fixture()
        env['root'].catalog['dummy'] = CatalogFieldIndex('hello!')
        self.assertRaises(CatalogError, self._fut, env = env)

    def test_check_detects_duplicate_key(self):
        env = self._fixture()
        self.config.add_catalog_indexes(__name__, {'title': CatalogFieldIndex('other')})
        self.assertRaises(CatalogError, self._fut, env = env)

    def test_check_detects_other_discriminator(self):
        env = self._fixture()
        env['root'].catalog['title'].discriminator = 'hello!'
        self.assertRaises(CatalogError, self._fut, env = env)

    def test_other_than_root_aborts(self):
        env = self._fixture()
        env['root'] = testing.DummyResource()
        self._fut(env = env)
