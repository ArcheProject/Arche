from __future__ import unicode_literals

from unittest import TestCase

from pyramid import testing
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPInsufficientStorage


class JSONFormatExcTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.views.exceptions import json_format_exc
        return json_format_exc

    def test_403(self):
        request = testing.DummyRequest()
        exc = HTTPForbidden("Not allowed")
        self.assertEqual(
            self._fut(request, exc),
            {'body': '', 'code': 403, 'message': "Not allowed", 'title': 'Forbidden'}
        )

    def test_404(self):
        request = testing.DummyRequest()
        exc = HTTPNotFound("Where did i...")
        self.assertEqual(
            self._fut(request, exc),
            {'body': '', 'code': 404, 'message': u"Where did i...", 'title': 'Not Found'}
        )

    def test_507(self):
        request = testing.DummyRequest()
        exc = HTTPInsufficientStorage("It's over!")
        self.assertEqual(
            self._fut(request, exc),
            {'body': '', 'code': 507, 'message': u"It's over!", 'title': 'Insufficient Storage'}
        )

    def test_base(self):
        request = testing.DummyRequest()
        exc = Exception("Any old base")
        self.assertEqual(
            self._fut(request, exc),
            {'body': None, 'code': 500, 'message': u"Any old base", 'title': 'Application error'}
        )

    def test_refguard(self):
        from arche.exceptions import ReferenceGuarded
        context = testing.DummyResource()
        def refguard():
            return [testing.DummyResource()]
        request = testing.DummyRequest()
        exc = ReferenceGuarded(context, refguard, guarded=(context,))
        res = self._fut(request, exc)
        self.assertEqual(res['code'], 500)
        self.assertEqual(res['title'], "Reference guarded error")
