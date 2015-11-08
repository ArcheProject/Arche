# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from unittest import TestCase

from fanstatic import clear_needed
from fanstatic import get_needed
from fanstatic import init_needed
from pyramid import testing


def _dummy_view(*args):
    return {}


class GetViewTests(TestCase):
    
    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.utils import get_view
        return get_view

    def _fixture(self, name = ''):
        self.config.add_view(_dummy_view, context=testing.DummyResource, name = name)

    def test_no_view(self):
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.assertEqual(self._fut(context, request), None)

    def test_default_view(self):
        self._fixture()
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.failUnless(self._fut(context, request))

    def test_named_view(self):
        self._fixture(name = 'hello')
        context = testing.DummyResource()
        request = testing.DummyRequest()
        self.failUnless(self._fut(context, request, view_name = 'hello'))


class GenerateSlugTests(TestCase):

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request = request)

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.utils import generate_slug
        return generate_slug

    def test_chineese(self):
        context = testing.DummyResource()
        hello = "您好"
        self.assertEqual(self._fut(context, hello), "nin-hao")

    def test_ukranian(self):
        context = testing.DummyResource()
        hello = "Привіт"
        self.assertEqual(self._fut(context, hello), "privit")

    def test_swedish(self):
        context = testing.DummyResource()
        text = "Héj åäö"
        self.assertEqual(self._fut(context, text), "hej-aao")

    def test_registered_views(self):
        self.config.add_view(_dummy_view, name = 'dummy', context = testing.DummyResource)
        context = testing.DummyResource()
        self.assertEqual(self._fut(context, 'dummy'), "dummy-1")

    def test_with_existing_keys(self):
        context = testing.DummyResource()
        context['hello'] = testing.DummyResource()
        self.assertEqual(self._fut(context, 'hello'), "hello-1")


class PrepHTMLForSearchTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()

    def tearDown(self):
        testing.tearDown()

    @property
    def _fut(self):
        from arche.utils import prep_html_for_search_indexing
        return prep_html_for_search_indexing

    def test_with_html_entities(self):
        self.assertEqual(self._fut("&aring;"), "å")

    def test_with_html(self):
        html = """
        <p>I read this <i>really</i> interesting article on
        <a href="http://www.wikipedia.org">Wikipedia</a> the other day.
        """
        plaintext = """
        I read this really interesting article on Wikipedia the other day.
        """.strip()
        self.assertEqual(self._fut(html), plaintext)

    def test_with_script(self):
        html = """
        <p>I'm just a paragraph</p>
        <script type="text/javascript"> And I'm a script //with a comment</script> """
        plaintext = "I'm just a paragraph"
        self.assertEqual(self._fut(html), plaintext)


class ReplaceFanstaticResourceTests(TestCase):

    def setUp(self):
        self.config = testing.setUp()
        init_needed()

    def tearDown(self):
        testing.tearDown()
        clear_needed()

    def test_integration(self):
        self.config.include('arche.utils')
        self.assertTrue(hasattr(self.config, 'replace_fanstatic_resource'))

    def test_replace_bootstrap(self):
        #replace bootstrap css with pure_js
        from arche.fanstatic_lib import main_css
        from arche.fanstatic_lib import pure_js
        from js.bootstrap import bootstrap_css
        self.config.include('arche.utils')
        self.config.replace_fanstatic_resource(bootstrap_css, pure_js)
        main_css.need()
        will_include = get_needed().resources()
        self.assertIn(pure_js, will_include)
        self.assertIn(main_css, will_include)
        self.assertNotIn(bootstrap_css, will_include)
