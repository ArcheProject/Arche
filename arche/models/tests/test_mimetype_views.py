# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from pyramid import testing
from pyramid.response import Response

class MIMETypeViewsTests(TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.mimetype_views import MIMETypeViews
        return MIMETypeViews
    
    def test_get_mimetype(self):
        obj = self._cut()
        obj['video/mp4'] = 'hello'
        self.assertEqual(obj['video/mp4'], 'hello') 
        
    def test_get_with_generic_type(self):
        obj = self._cut()
        obj['video/*'] = 'hello'
        self.assertEqual(obj['video/mp4'], 'hello')
        
    def test_contains_with_generic(self):
        obj = self._cut()
        obj['video/*'] = 'hello'
        self.assertIn('video/hello', obj)
        
    def test_get_with_generic(self):
        obj = self._cut()
        obj['video/mp4'] = 'hello'
        self.assertEqual(obj.get('video/mp4'), 'hello')
        self.assertEqual(obj.get('video/something'), None)
        obj['video/*'] = 'world'
        self.assertEqual(obj.get('video/mp4'), 'hello')
        self.assertEqual(obj.get('video/something'), 'world')
        self.assertEqual(obj.get('video/*'), 'world')
        
    def test_get_mimetype_views(self):
        self.config.include('arche.models.mimetype_views')
        self.config.add_mimetype_view('dummy/text', 'a_view')
        from arche.utils import get_mimetype_views
        self.assertIsInstance(get_mimetype_views(), self._cut)
        
    def test_integration(self):
        self.config.include('arche.models.mimetype_views')
        from arche.views.file import mimetype_view_selector
        self.config.add_mimetype_view('test/*', 'helloworld')
        
        class DummyContext(testing.DummyResource):
            mimetype = 'test/boo'
            
        L = []
        def dummy_view(*args):
            L.append(args)
            return ''
            
        self.config.add_view(dummy_view, context=DummyContext, name='helloworld', renderer='string')
        context = DummyContext()
        request = testing.DummyRequest()
        result = mimetype_view_selector(context, request)
        self.assertEqual(len(L), 1)
        self.assertIsInstance(result, Response)
