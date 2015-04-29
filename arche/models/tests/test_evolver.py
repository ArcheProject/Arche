from __future__ import unicode_literals
from unittest import TestCase

from pyramid import testing
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
from arche.interfaces import IEvolver
from zope.interface import implementer
from arche.interfaces import IRoot
from arche.exceptions import EvolverVersionError


class _MockJar(object):
    _root = {}

    def root(self):
        return self._root

@implementer(IRoot)
class _MockPersistentLike(testing.DummyResource):
    _p_jar = None

    def __init__(self):
        self._p_jar = _MockJar()


class BaseEvolverTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp()
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.evolver import BaseEvolver
        return BaseEvolver

    def test_verify_class(self):
        self.failUnless(verifyClass(IEvolver, self._cut))

    def test_verify_object(self):
        context = _MockPersistentLike()
        self.failUnless(verifyObject(IEvolver, self._cut(context)))

    def test_needs_upgrade(self):
        obj = self._cut(_MockPersistentLike())
        obj.sw_version = 1
        self.assertTrue(obj.needs_upgrade)

    def test_check_requirements(self):
        class _Evolver1(self._cut):
            name = 'one'
            version_requirements = {'two': 2}
        class _Evolver2(self._cut):
            name = 'two'
            db_version = 0
        self.config.registry.registerAdapter(_Evolver2, name = 'two')
        root = _MockPersistentLike()
        one = _Evolver1(root)
        self.assertEqual(one.check_requirements(), {'two': 0})
        _Evolver2.db_version = 2
        self.assertEqual(one.check_requirements(), {})

    def test_evolve_blocked_due_to_requirement(self):
        class _Evolver1(self._cut):
            name = 'one'
            sw_version = 1
            version_requirements = {'two': 2}
        class _Evolver2(self._cut):
            name = 'two'
            db_version = 0
        self.config.registry.registerAdapter(_Evolver2, name = 'two')
        root = _MockPersistentLike()
        one = _Evolver1(root)
        self.assertRaises(EvolverVersionError, one.evolve)

    def test_evolve(self):
        class _Evolver(self._cut):
            name = 'one'
            sw_version = 1
            evolve_packagename = 'arche.models.tests.evolve_fixture'
        root = _MockPersistentLike()
        obj = _Evolver(root)
        obj.evolve()
        self.assertEqual(root.evolved, True)
