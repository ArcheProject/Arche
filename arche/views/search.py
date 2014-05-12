from repoze.catalog.query import Eq
from repoze.catalog.query import Contains
from repoze.catalog.query import Name
from repoze.catalog.query import Any
from zope.index.text.parsetree import ParseError
from pyramid.traversal import resource_path
from pyramid.traversal import find_resource
from pyramid.view import view_config, view_defaults

from arche.views.base import BaseView
from arche import security
from arche import _


@view_defaults(permission = security.PERM_VIEW, context = 'arche.interfaces.IRoot')
class SearchView(BaseView):

    def _mk_query(self):
        self.docids = ()
        query = self.request.GET.get('query', None)
        if not query:
            return
        if self.request.GET.get('glob', False):
            if '*' not in query:
                query = "%s*" % query
        query_obj = Contains('searchable_text', query) & Eq('search_visible', True)
        type_name = self.request.GET.getall('type_name')
        if type_name:
            query_obj &= Any('type_name', type_name)
        try:
            self.docids = self.root.catalog.query(query_obj)[1]
        except ParseError:
            if not self.request.is_xhr:
                msg = _(u"Invalid search query - try something else!")
                self.flash_messages.add(msg, type="danger")
            
    @view_config(name = 'search', renderer = 'arche:templates/search.pt')
    def search_page(self):
        self._mk_query()
        return {'results': self.resolve_docids(self.docids)}

    @view_config(name = 'search.json', renderer = 'json')
    def search_json(self):
        self._mk_query()
        output = []
        for obj in self.resolve_docids(self.docids):
            output.append({'text': obj.title,
                           'id': obj.uid,
                           'type_name': obj.type_name,
                           'img_tag': self.thumb_tag(obj, 'mini'),
                           'type_title': getattr(obj, 'type_title', obj.type_name)})
        return {'results': output}


def includeme(config):
    config.scan('.search')
