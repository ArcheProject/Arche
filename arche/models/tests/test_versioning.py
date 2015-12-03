from unittest import TestCase
from datetime import datetime

from pyramid import testing
from zope.interface import implementer
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.api import BaseMixin
from arche.api import ContextACLMixin
from arche.interfaces import IContent
from arche.interfaces import IRevisions
from arche.interfaces import ITrackRevisions
from arche.testing import barebone_fixture


@implementer(IContent, ITrackRevisions)
class _DummyContent(testing.DummyResource, BaseMixin, ContextACLMixin):
    type_name = 'Dummy'
    title = 'Hello world'
    description = ''


class _DummyEvent(object):
    def __init__(self, changed):
        self.changed = changed
    

class RevisionsTests(TestCase):    
    
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.models.versioning')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.versioning import Revisions
        return Revisions

    def test_verify(self):
        self.failUnless(verifyClass(IRevisions, self._cut))
        self.failUnless(verifyObject(IRevisions, self._cut(_DummyContent())))

    def test_new_nothing_registered(self):
        context = _DummyContent()
        request = testing.DummyRequest()
        event = _DummyEvent(('a', 'b', 'title'))
        obj = self._cut(context)
        obj.new(event, request)
        self.failIf(len(obj))

    def test_new_check_some(self):
        self.config.add_versioning('Dummy', ['title'])
        context = _DummyContent()
        request = testing.DummyRequest()
        event = _DummyEvent(('a', 'b', 'title'))
        obj = self._cut(context)
        obj.new(event, request)
        self.failUnless(len(obj))
        self.assertEqual(obj[0]['title'], "Hello world")

    def test_new_fetches_all_if_event_changed_is_none(self):
        self.config.add_versioning('Dummy', ['title'])
        context = _DummyContent()
        request = testing.DummyRequest()
        event = _DummyEvent(None)
        obj = self._cut(context)
        obj.new(event, request)
        self.failUnless(len(obj))

    def test_new_sets_datetime(self):
        self.config.add_versioning('Dummy', ['title'])
        context = _DummyContent()
        request = testing.DummyRequest()
        event = _DummyEvent(None)
        obj = self._cut(context)
        obj.new(event, request)
        self.failUnless(isinstance(obj[0].timestamp, datetime))

    def test_new_userid(self):
        self.config.testing_securitypolicy('jane_doe')
        self.config.add_versioning('Dummy', ['title'])
        context = _DummyContent()
        request = testing.DummyRequest()
        event = _DummyEvent(None)
        obj = self._cut(context)
        obj.new(event, request)
        self.assertEqual(obj[0].userid, 'jane_doe')

    def test_get_tracked_attributes(self):
        self.config.add_versioning('Dummy', ['title'])
        self.config.add_versioning(IContent, ['other'])
        first_context = _DummyContent()
        second_context = _DummyContent()
        second_context.type_name = 'Second'
        first = self._cut(first_context)
        self.assertEqual(first.get_tracked_attributes(self.config.registry), set(['title', 'other']))
        second = self._cut(second_context)
        self.assertEqual(second.get_tracked_attributes(self.config.registry), set(['other']))
        third = self._cut(object())
        self.assertEqual(third.get_tracked_attributes(self.config.registry), set([]))

    def test_adapter_registers_as_true(self):
        self.assertTrue(self._cut(None))

    def test_get_revisions(self):
        self.config.testing_securitypolicy('jane_doe')
        self.config.add_versioning('Dummy', ['title', 'description'])
        context = _DummyContent()
        request = testing.DummyRequest()
        event = _DummyEvent(None)
        obj = self._cut(context)
        obj.new(event, request)
        from arche.models.versioning import Revision
        for i in range(0, 10, 2):
            rev = Revision('jane', {'title': str(i), 'description': str(i)}, i)
            obj.data[i] = rev
        for i in range(1, 11, 2):
            rev = Revision('john', {'title': str(i)}, i)
            obj.data[i] = rev
        revisions = tuple(obj.get_revisions('title', limit = 5))
        self.assertEqual([x.id for x in revisions], [9, 8, 7, 6, 5])
        revisions = tuple(obj.get_revisions('description', limit = 10))
        self.assertEqual([x.id for x in revisions], [8, 6, 4, 2, 0])


class VersioningIntegrationTests(TestCase):

    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())
        self.config.include('arche.models.versioning')

    def tearDown(self):
        testing.tearDown()

    def test_add_stores_data(self):
        root = barebone_fixture(self.config)
        self.config.add_versioning(IContent, ['title'])
        root['a'] = context = _DummyContent(title = "What's up?")
        obj = IRevisions(context, {})
        self.assertEqual(obj[0]['title'], "What's up?")

    def test_update_stores_data(self):
        root = barebone_fixture(self.config)
        self.config.add_versioning(IContent, ['title'])
        root['a'] = context = _DummyContent(title = "What's up?")
        obj = IRevisions(context, {})
        context.update(title = "Hello world")
        obj = IRevisions(context)
        self.assertEqual(len(obj), 2)
        self.assertEqual(obj[1]['title'], "Hello world")

    def test_add_wrong_type(self):
        self.assertRaises(TypeError, self.config.add_versioning, {}, [])
        self.assertRaises(TypeError, self.config.add_versioning, object, [])
