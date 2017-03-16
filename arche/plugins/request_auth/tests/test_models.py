from datetime import datetime
from unittest import TestCase

from colander import Invalid
from pyramid import testing
from pyramid.httpexceptions import HTTPFound
from zope.interface.verify import verifyClass, verifyObject

from arche.api import User
from arche.interfaces import IWillLoginEvent
from arche.plugins.request_auth.exceptions import ConsumeTokenError
from arche.plugins.request_auth.interfaces import IRequestSession
from arche.testing import barebone_fixture, init_request_methods


class RequestSessionTests(TestCase):
    
    def setUp(self):
        self.request = testing.DummyRequest(client_addr = '127.0.0.1', user_agent = 'Testing Browser')
        self.config = testing.setUp(request = self.request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.plugins.request_auth.models import RequestSession
        return RequestSession

    def test_validate_cls(self):
        self.failUnless(verifyClass(IRequestSession, self._cut))

    def test_validate_obj(self):
        self.failUnless(verifyObject(IRequestSession, self._cut(self.request)))

    def _fixture(self):
        self.config.include('arche.testing')
        self.config.include('arche.plugins.request_auth')
        root = barebone_fixture(self.config)
        root['users']['robot'] = User()
        root['users']['jane'] = User()
        self.request.root = root
        init_request_methods(self.request)
        return root

    def _pop_request(self, **kw):
        data = dict(
            userid = 'jane',
            client_ip = '127.0.0.1',
            login_max_valid = 40,
            link_valid = 30,
            redirect_url = 'http://hello.world'
        )
        data.update(**kw)
        self.request.POST.update(data)

    def test_new(self):
        root = self._fixture()
        obj = self._cut(root)
        obj.new(self.request, 'userid')
        self.assertEqual(len(obj), 1)

    def test_new_from_request(self):
        root = self._fixture()
        obj = self._cut(root)
        data = dict(
            userid = 'jane',
            client_ip = '127.0.0.1',
            login_max_valid = 40,
            link_valid = 30,
            redirect_url = 'http://hello.world',
        )
        self.request.POST.update(data)
        obj.new_from_request(self.request)
        self.assertEqual(obj['jane']['client_ip'], '127.0.0.1')
        self.assertEqual(obj['jane']['login_max_valid'], 40)
        self.assertIsInstance(obj['jane']['link_valid'], datetime)
        self.assertEqual(obj['jane']['redirect_url'], 'http://hello.world')

    def test_get_data(self):
        root = self._fixture()
        obj = self._cut(root)
        data = dict(
            userid = 'jane',
            client_ip = '127.0.0.1',
            login_max_valid = 40,
            link_valid = 30,
            redirect_url = 'http://hello.world',
        )
        self.request.POST.update(data)
        self.assertEqual(obj.get_data(self.request), data)

    def test_get_data_validation_error(self):
        root = self._fixture()
        obj = self._cut(root)
        data = dict(
           # userid = 'jane',
            client_ip = '127.0.0.1',
            login_max_valid = 40,
            link_valid = 30,
            redirect_url = 'http://hello.world',
        )
        self.request.POST.update(data)
        self.assertRaises(Invalid, obj.get_data, self.request)

    def test_consume(self):
        root = self._fixture()
        obj = self._cut(root)
        obj.new(self.request, 'userid', redirect_url='http://betahaus.net')
        self.assertIn('userid', obj)
        res = obj.consume(self.request, 'userid')
        self.assertEqual(res.location, 'http://betahaus.net')
        self.assertNotIn('userid', obj)

    def test_consume_fires_event_if_user_exists(self):
        root = self._fixture()
        obj = self._cut(root)
        obj.new(self.request, 'userid')
        obj.new(self.request, 'jane')
        L = []
        def _subs(event):
            L.append(event)
        self.config.add_subscriber(_subs, IWillLoginEvent)
        obj.consume(self.request, 'userid')
        self.assertEqual(len(L), 0)
        obj.consume(self.request, 'jane')
        self.assertEqual(len(L), 1)

    def test_consume_from_request(self):
        root = self._fixture()
        obj = self._cut(root)
        obj.new(self.request, 'userid', client_ip='127.0.0.1')
        obj['userid']['token'] = 'abc'
        request = testing.DummyRequest(
            client_addr = '127.0.0.1',
            user_agent = 'Testing Browser',
            subpath = ['abc'],
        )
        self.assertIsInstance(obj.consume_from_request(request), HTTPFound)

    def test_consume_from_request_bad_request(self):
        root = self._fixture()
        obj = self._cut(root)
        obj.new(self.request, 'userid', client_ip='127.0.0.1')
        obj['userid']['token'] = 'abc'
        request = testing.DummyRequest(
            client_addr = '127.0.0.1',
            user_agent = 'Testing Browser',
            subpath = ['BAD-AND-WRONG'],
        )
        self.assertRaises(ConsumeTokenError, obj.consume_from_request, request)
