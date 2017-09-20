from pyramid.i18n import TranslationString
from pyramid.view import view_config
from pyramid.view import view_defaults
from repoze.catalog.query import Any
from repoze.catalog.query import Contains
from repoze.catalog.query import Eq
from six import string_types
from zope.index.text.parsetree import ParseError

from arche import _
from arche import security
from arche.views.base import BaseView


@view_defaults(permission = security.PERM_VIEW, context = 'arche.interfaces.IRoot')
class SearchView(BaseView):

    def _mk_query(self):
        self.docids = ()
        query_objs = []
        if not self.request.GET.get('show_hidden', False):
            query_objs.append(Eq('search_visible', True))
        query = self.request.GET.get('query', None)
        perform_query = False
        if query:
            if self.request.GET.get('glob', False):
                if '*' not in query:
                    query = "%s*" % query
            query_objs.append(Contains('searchable_text', query))
            perform_query = True
        #Check other get-values:
        #FIXME: This should be smarter, and should perhaps be able to handle glob, other types of queries etc.
        for (k, v) in self.request.GET.mixed().items():
            if v and k in self.root.catalog:
                perform_query = True
                if isinstance(v, string_types):
                    query_objs.append(Eq(k, v))
                else:
                    query_objs.append(Any(k, v))
        query_obj = None
        if not query_objs or perform_query == False:
            return
        for obj in query_objs:
            #There must be a smarter way to do this, right?
            try:
                query_obj &= obj
            except TypeError:
                query_obj = obj
        try:
            self.docids = self.root.catalog.query(query_obj)[1]
        except ParseError:
            if not self.request.is_xhr:
                msg = _(u"Invalid search query - try something else!")
                self.flash_messages.add(msg, type="danger")
            
    @view_config(name = 'search', renderer = 'arche:templates/search.pt')
    def search_page(self):
        self._mk_query()
        return {'results': tuple(self.resolve_docids(self.docids)),
                'query': self.request.GET.get('query', ''),}

    @view_config(name = 'search.json', renderer = 'json')
    def search_json(self):
        self._mk_query()
        output = []
        for obj in self.resolve_docids(self.docids):
            type_title = getattr(obj, 'type_title', obj.type_name)
            if isinstance(type_title, TranslationString):
                type_title = self.request.localizer.translate(type_title)
            output.append({'text': obj.title,
                           'id': obj.uid,
                           'type_name': obj.type_name,
                           'img_tag': self.thumb_tag(obj, 'mini'),
                           'type_title': type_title})
        return {'results': output}


def includeme(config):
    config.scan('.search')
