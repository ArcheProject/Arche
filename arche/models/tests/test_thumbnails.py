from unittest import TestCase

from pyramid import testing
from zope.interface import implementer
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject

from arche.interfaces import IThumbnailedContent
from arche.interfaces import IThumbnails
from arche.interfaces import IThumbnailsCache


class ThumbnailsTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.thumbnails import Thumbnails
        return Thumbnails

    def test_verify_class(self):
        self.failUnless(verifyClass(IThumbnails, self._cut))

    def test_verify_obj(self):
        self.failUnless(verifyObject(IThumbnails, self._cut(testing.DummyModel())))

    def test_integration(self):
        self.config.include('arche.models.thumbnails')
        @implementer(IThumbnailedContent)
        class _Dummy(testing.DummyModel):
            pass
        context = _Dummy()
        obj = IThumbnails(context, None)
        self.assertIsInstance(obj, self._cut)


class ThumbnailsCacheTests(TestCase):
    """ Make sure integration with LRU-cache works
    """

    def setUp(self):
        self.config = testing.setUp()
        self.config.include('arche.models.thumbnails')

    def tearDown(self):
        testing.tearDown()

    def test_integration(self):
        cache = self.config.registry.queryUtility(IThumbnailsCache)
        self.failUnless(IThumbnailsCache.providedBy(cache))

    def test_iface(self):
        cache = self.config.registry.queryUtility(IThumbnailsCache)
        self.failUnless(verifyObject(IThumbnailsCache, cache))
