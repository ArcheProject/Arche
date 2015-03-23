import unittest

from pyramid import testing
from pyramid.session import UnencryptedCookieSessionFactoryConfig
from zope.interface.verify import verifyClass
from zope.interface.verify import verifyObject
import transaction

from arche.interfaces import IFlashMessages


class FlashMessagesTests(unittest.TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.flash_messages import FlashMessages
        return FlashMessages

    def _dummy_request(self):
        request = testing.DummyRequest()
        request.session = UnencryptedCookieSessionFactoryConfig('messages')(request)
        return request

    def test_verify_class(self):
        self.assertTrue(verifyClass(IFlashMessages, self._cut))

    def test_verify_obj(self):
        #It's okay to adapt none if we don't check the adapted context in __init__
        self.assertTrue(verifyObject(IFlashMessages, self._cut(self._dummy_request())))

    def test_add_simple(self):
        request = self._dummy_request()
        obj = self._cut(request)
        obj.add("Message", require_commit = False)
        res = [x for x in request.session.pop_flash()]
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['msg'], "Message")

    def test_add_with_transaction(self):
        transaction.begin()
        request = self._dummy_request()
        obj = self._cut(request)
        obj.add("Message")
        res = [x for x in request.session.pop_flash()]
        self.assertEqual(len(res), 0) #Nothing added without commit
        transaction.commit()
        res = [x for x in request.session.pop_flash()]
        self.assertEqual(len(res), 1)

    def test_add_with_transaction_abort(self):
        transaction.begin()
        request = self._dummy_request()
        obj = self._cut(request)
        obj.add("Message")
        res = [x for x in request.session.pop_flash()]
        self.assertEqual(len(res), 0) #Nothing added without commit
        transaction.abort()
        res = [x for x in request.session.pop_flash()]
        self.assertEqual(len(res), 0)

    def test_get_messages(self):
        request = self._dummy_request()
        request.session.flash({'msg': 'Hello world'})
        obj = self._cut(request)
        res = [x for x in obj.get_messages()]
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['msg'], 'Hello world')

    def test_render(self):
        self.config.include('pyramid_chameleon')
        request = self._dummy_request()
        obj = self._cut(request)
        obj.add("I am a message", require_commit = False)
        response = obj.render()
        self.assertIn("I am a message", response)
        
    def test_register_adapter(self):
        self.config.include('arche.models.flash_messages')
        request = testing.DummyRequest()
        self.assertTrue(self.config.registry.queryAdapter(request, IFlashMessages))
