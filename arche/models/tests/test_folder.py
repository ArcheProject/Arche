from unittest import TestCase

from arche.interfaces import IArcheFolder
from pyramid import testing
from zope.interface.verify import verifyClass, verifyObject


class FolderTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.folder import ArcheFolder
        return ArcheFolder

    def test_verify_class(self):
        self.failUnless(verifyClass(IArcheFolder, self._cut))

    def test_verify_obj(self):
        self.failUnless(verifyObject(IArcheFolder, self._cut()))
