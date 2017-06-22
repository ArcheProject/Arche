# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from unittest import TestCase

from pyramid import testing
from pyramid.request import apply_request_extensions
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.interfaces import IUser
from arche.interfaces import IDocument
from arche.interfaces import IReferenceGuards
from arche.exceptions import ReferenceGuarded
from arche.testing import barebone_fixture


class RefGuardTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.reference_guard import RefGuard
        return RefGuard

    def _fixture(self):
        from arche.resources import User
        root = barebone_fixture(self.config)
        root['users']['jane'] = User(email = 'hello@betahaus.net')
        return root

    def test_guarded_iface_respected(self):
        from arche.resources import Document
        request = testing.DummyRequest()
        context = testing.DummyModel()

        def _checker(*args):
            return [1, 2]

        obj = self._cut(_checker)
        self.assertFalse(obj(request, context))
        context = Document()
        self.assertRaises(ReferenceGuarded, obj, request, context)

    def test_get_guarded_count_simple(self):
        request = testing.DummyRequest()
        root = self._fixture()

        def _checker(*args):
            return [1, 2]

        obj = self._cut(_checker)
        self.assertEqual(obj.get_guarded_count(request, root), 2)

    def test_get_guarded_count_catalog_result(self):
        from arche.resources import Document
        request = testing.DummyRequest()
        root = self._fixture()
        root['doc1'] = Document()
        root['doc2'] = Document()
        root['doc3'] = Document()

        def _checker(request, context):
            """ Return all documents..."""
            return root.catalog.query("type_name == 'Document'")

        obj = self._cut(_checker, catalog_result=True)
        self.assertEqual(obj.get_guarded_count(request, root), 3)

    def test_get_guarded_objects_simple(self):
        request = testing.DummyRequest()
        root = self._fixture()

        def _checker(*args):
            return [1, 2]

        obj = self._cut(_checker)
        self.assertEqual(tuple(obj.get_guarded_objects(request, root)), (1, 2))
        self.assertTrue(hasattr(obj.get_guarded_objects(request, root), 'next'))

    def test_get_guarded_objects_catalog_result(self):
        from arche.resources import Document
        root = self._fixture()
        request = testing.DummyRequest()
        apply_request_extensions(request)
        request.root = root
        root['doc1'] = doc1 = Document()
        root['doc2'] = doc2 = Document()

        def _checker(*args):
            return root.catalog.query("type_name == 'Document'")

        obj = self._cut(_checker, catalog_result=True)
        self.assertEqual(set(obj.get_guarded_objects(request, root)),
                         set([doc1, doc2]))
        self.assertTrue(hasattr(obj.get_guarded_objects(request, root), 'next'))

    def test_get_guarded_objects_with_limit(self):
        root = self._fixture()
        request = testing.DummyRequest()

        def _checker(*args):
            return range(10)

        obj = self._cut(_checker)
        self.assertEqual(set(obj.get_guarded_objects(request, root, limit=5)),
                         set(range(5)))
        self.assertTrue(hasattr(obj.get_guarded_objects(request, root), 'next'))

    def test_get_guarded_objects_with_no_limit(self):
        root = self._fixture()
        request = testing.DummyRequest()

        def _checker(*args):
            return range(10)

        obj = self._cut(_checker)
        self.assertEqual(set(obj.get_guarded_objects(request, root, limit=0)),
                         set(range(10)))
        self.assertTrue(hasattr(obj.get_guarded_objects(request, root), 'next'))

    def test_get_guarded_objects_with_no_result(self):
        root = self._fixture()
        request = testing.DummyRequest()

        def _checker(*args):
            return []

        obj = self._cut(_checker)
        self.assertEqual(set(obj.get_guarded_objects(request, root)),
                         set([]))
        self.assertTrue(hasattr(obj.get_guarded_objects(request, root), 'next'))
        empty_gen = obj.get_guarded_objects(request, root)
        self.assertRaises(StopIteration, empty_gen.next)

    def test_get_wrong_context_has_same_behaviour(self):
        root = self._fixture()
        request = testing.DummyRequest()

        def _checker(*args):
            return []

        obj = self._cut(_checker, requires=[IUser])
        self.assertEqual(set(obj.get_guarded_objects(request, root)),
                         set([]))
        self.assertTrue(hasattr(obj.get_guarded_objects(request, root), 'next'))
        empty_gen = obj.get_guarded_objects(request, root)
        self.assertRaises(StopIteration, empty_gen.next)


class ReferenceGuardsTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        self.config.include('arche.models.reference_guard')

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.reference_guard import ReferenceGuards
        return ReferenceGuards

    def _fixture(self):
        from arche.resources import User
        from arche.resources import Document
        root = barebone_fixture(self.config)
        root['users']['jane'] = User()
        root['doc'] = Document()
        return root

    def test_iface(self):
        self.assertTrue(verifyClass(IReferenceGuards, self._cut))
        self.assertTrue(verifyObject(IReferenceGuards, self._cut(testing.DummyRequest())))

    def test_get_valid(self):
        def _rg(*args):
            return []
        self.config.add_ref_guard(_rg, requires=[IUser])
        root = self._fixture()
        request = testing.DummyRequest()
        obj = self._cut(request)
        self.assertFalse(tuple(obj.get_valid(root)))
        self.assertTrue(tuple(obj.get_valid(root['users']['jane'])))

    def test_check(self):
        def _rg(*args):
            #Anything goes!
            return [1, 2, 3]
        root = self._fixture()
        request = testing.DummyRequest()
        obj = self._cut(request)
        self.assertFalse(obj.check(root['doc']))
        self.config.add_ref_guard(_rg, requires=[IDocument])
        self.assertRaises(ReferenceGuarded, obj.check, root['doc'])

    def test_get_vetoing(self):
        def _rg(*args):
            return [1, 2, 3]
        root = self._fixture()
        request = testing.DummyRequest()
        obj = self._cut(request)
        self.assertFalse(tuple(obj.get_vetoing(root['doc'])))
        self.config.add_ref_guard(_rg, requires=[IDocument])
        self.assertTrue(tuple(obj.get_vetoing(root['doc'])))

    def test_moving_allows_bypass_check(self):
        def _rg(*args):
            return [1, 2, 3]
        root = self._fixture()
        request = testing.DummyRequest()
        obj = self._cut(request)
        self.config.add_ref_guard(_rg, requires=[IDocument])
        self.assertTrue(tuple(obj.get_vetoing(root['doc'])))
        obj = self._cut(request)
        obj.moving(root['doc'].uid)
        self.assertFalse(tuple(obj.get_vetoing(root['doc'])))

    def test_moving_bypass_not_allowed(self):
        def _rg(*args):
            return [1, 2, 3]
        root = self._fixture()
        request = testing.DummyRequest()
        obj = self._cut(request)
        self.config.add_ref_guard(_rg, requires=[IDocument], allow_move=False)
        obj.moving(root['doc'].uid)
        self.assertTrue(tuple(obj.get_vetoing(root['doc'])))


class RefGuardIntegrationTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.testing')
        self.config.include('arche.testing.catalog')
        self.config.include('arche.models.reference_guard')

    def tearDown(self):
        testing.tearDown()

    def _fixture(self):
        from arche.resources import User
        root = barebone_fixture(self.config)
        root['users']['jane'] = User(email = 'jane.doe@betahaus.net')
        request = testing.DummyRequest()
        apply_request_extensions(request)
        self.config.begin(request)
        request.root = root
        return root, request

    def test_integration(self):
        from arche.resources import Document
        root, request = self._fixture()
        root['doc'] = Document()

        def stop_delete_user(request, context):
            if context.type_name == 'User':
                return [context]

        self.config.add_ref_guard(stop_delete_user, requires=[IUser])
        try:
            del root['doc']
        except ReferenceGuarded:
            self.fail("ReferenceGuarded raised on wrong context")

        def _del_user():
            del root['users']['jane']

        self.assertRaises(ReferenceGuarded, _del_user)
