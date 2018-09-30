# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

from pyramid import testing
from pyramid.request import apply_request_extensions
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.query import Contains
from zope.component import adapter
from zope.interface import implementer
from zope.interface.exceptions import BrokenMethodImplementation
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.exceptions import CatalogConfigError
from arche.interfaces import ICataloger
from arche.interfaces import IIndexedContent
from arche.interfaces import IMetadata


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
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')

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

    def test_tags_index(self):
        root = self._fixture()
        context = self._mk_context()
        context.tags = ['one', 'TWO']
        root['a'] = context
        obj = self._cut(context)
        obj.index_object()
        self.assertEqual(1, obj.catalog.query("tags == 'one'")[0])
        self.assertEqual(1, obj.catalog.query("tags == 'two'")[0])
        self.assertEqual(0, obj.catalog.query("tags == 'TWO'")[0])

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

    def test_searchable_html_body(self):
        root = self._fixture()
        context = self._mk_context()
        context.body = """
        <p>I'm a paragraph</p>
        <b>Örebro is a swedish town</b>
        <i>"您好"</i> is hello in chineese.
        <script>Is bad stuff here</script>
        """
        root['a'] = context
        obj = self._cut(context)
        obj.index_object()
        cq = obj.catalog.query
        self.assertEqual(cq(Contains("searchable_text", 'paragraph'))[0], 1)
        self.assertEqual(cq(Contains("searchable_text", 'Örebro'))[0], 1)
        self.assertEqual(cq(Contains("searchable_text", '您好'))[0], 1)
        self.assertEqual(cq(Contains("searchable_text", 'stuff'))[0], 0)

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
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        self.config.add_metadata_field(self._dummy_metadata)
        context = self._mk_context()
        self.failUnless(self.config.registry.queryAdapter(context, IMetadata, name = 'dummy'))

    def test_integration_get_metadata(self):
        self.config.include('arche.testing')
        self.config.include('arche.models.catalog')
        self.config.add_metadata_field(self._dummy_metadata)
        from arche.api import Root
        root = Root()
        root['c'] = context = self._mk_context()
        cataloger = ICataloger(context)
        self.assertEqual(cataloger.get_metadata(), {'dummy': 'Hello'})

    def test_metadata_added_on_index(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
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
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
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
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        def _callable():
            return 'Hello world'
        self.assertRaises(BrokenMethodImplementation, self.config.create_metadata_field, _callable, 'dummy')

    def test_integration_create_metadata_field_attribute(self):
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
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
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.models.catalog import check_catalog_on_startup
        return check_catalog_on_startup

    def _fixture(self):
        from arche.api import Root
        request = testing.DummyRequest()
        apply_request_extensions(request)
        request.root = root = Root()
        self.config.begin(request)
        return {'closer': object, 'root': root,
                'registry': self.config.registry, 'request': request}

    def test_check_catalog_on_startup(self):
        env = self._fixture()
        self._fut(env = env)

    def test_check_detects_missing(self):
        env = self._fixture()
        catalog = env['root'].catalog
        del catalog['title']
        self._fut(env=env)
        self.assertIn('title', catalog)

    def test_check_detects_too_many(self):
        env = self._fixture()
        env['root'].catalog['dummy'] = CatalogFieldIndex('hello!')
        self._fut(env=env)
        self.assertNotIn('dummy', env['root'].catalog)

    def test_check_detects_duplicate_key(self):
        env = self._fixture()
        self.config.add_catalog_indexes(__name__, {'title': CatalogFieldIndex('other')})
        self.assertRaises(CatalogConfigError, self._fut, env = env)

    def test_check_detects_other_discriminator(self):
        env = self._fixture()
        catalog = env['root'].catalog
        catalog['title'].discriminator = 'hello!'
        self._fut(env=env)
        self.assertNotEqual(catalog['title'].discriminator, 'hello!')

    def test_other_than_root_aborts(self):
        env = self._fixture()
        env['root'] = testing.DummyResource()
        self._fut(env = env)


class CatalogIndexHelperTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.testing')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.catalog import CatalogIndexHelper
        return CatalogIndexHelper

    def test_defaults(self):
        obj = self._cut()
        obj.update('hello')
        obj.update('world')
        self.assertEqual(obj.get_limit_types(['hello', 'world']), None)
        self.assertEqual(obj.get_required(['hello', 'world']), set(['hello', 'world']))
        self.assertEqual(obj['hello'].linked, set(['hello']))
        self.assertEqual(obj['hello'].type_names, None)

    def test_get_limit_types(self):
        obj = self._cut()
        obj.update('hello', type_names='Greet')
        obj.update('world')
        self.assertEqual(obj.get_limit_types(['hello']), set(['Greet']))
        self.assertEqual(obj.get_limit_types(['world']), None)
        self.assertEqual(obj.get_limit_types(['hello', 'world']), None)

    def test_get_required(self):
        obj = self._cut()
        obj.update('hello', linked=['niceness'])
        obj.update('hello', linked='politeness')
        obj.update('world')
        self.assertEqual(obj.get_required(['niceness']), set(['hello', 'niceness']))
        self.assertEqual(obj.get_required(['world']), set(['world']))
        self.assertEqual(obj.get_required(['hello', 'niceness']), set(['hello', 'niceness']))

    # def test_get_required_3_steps(self):
    #     obj = self._cut()
    #     obj.update('one', linked='two')
    #     obj.update('two', linked='three')
    #     self.assertEqual(obj.get_required(['one']), set(['one']))
    #     self.assertEqual(obj.get_required(['two']), set(['one', 'two']))
    #     self.assertEqual(obj.get_required(['three']), set(['one', 'two', 'three']))
    #
    # def test_get_required_circular(self):
    #     obj = self._cut()
    #     obj.update('one', linked='two')
    #     obj.update('two', linked='three')
    #     obj.update('three', linked='one')
    #     self.assertEqual(obj.get_required(['one']), set(['one', 'two', 'three']))

    def test_setting_none_as_marker_for_always(self):
        obj = self._cut()
        obj.update('hello', linked=None, type_names=None)
        self.assertEqual(obj.get_limit_types(['404']), None)
        self.assertEqual(obj.get_required(['world']), set(['hello', 'world']))
