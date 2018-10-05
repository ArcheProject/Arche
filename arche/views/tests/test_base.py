# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from pyramid import testing
import colander
from pyramid.request import apply_request_extensions

from arche.interfaces import IBaseForm
from arche.interfaces import IFormSuccessEvent


class BaseFormTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.views.base import BaseForm
        return BaseForm

    @property
    def _TestingForm(self):
        class TestingForm(self._cut):
            captured = []
            def save_success(self, appstruct):
                self.captured.append(appstruct)
        return TestingForm

    @property
    def _TestingSchema(self):
        class TestingSchema(colander.Schema):
            text = colander.SchemaNode(
                colander.String(),
            )
        return TestingSchema

    def _fixture(self):
        context = testing.DummyResource()
        request = testing.DummyRequest()
        #apply_request_extensions(request)
        return self._TestingForm(context, request, self._TestingSchema())

    def test_event_fired_on_success(self):
        form = self._fixture()
        form.request.POST.update(save='save', text='Hello')
        L = []
        def subs(obj, event):
            L.append((obj, event))
        self.config.add_subscriber(subs, [IBaseForm, IFormSuccessEvent])
        form()
        self.assertEqual(len(L), 1)
        self.assertEqual(L[0][1].appstruct, {'text': 'Hello'})
        self.assertEqual(L[0][0], form)

    def test_event_may_modify_appstruct(self):
        form = self._fixture()
        form.request.POST.update(save='save', text='Hello')
        def subs(obj, event):
            event.appstruct['world'] = 1
        self.config.add_subscriber(subs, [IBaseForm, IFormSuccessEvent])
        form()
        self.assertIn('world', form.captured[0])

    def test_failing_form_not_initial(self):
        form = self._fixture()
        form.request.POST.update(save='save', text='Hello')
        self.assertTrue(form.initial)
        form()
        self.assertTrue(form.initial)
        del form.request.POST['text']  # Will cause validation error
        form()
        self.assertFalse(form.initial)
