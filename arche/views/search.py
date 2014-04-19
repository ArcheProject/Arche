from repoze.catalog.query import Eq
from repoze.catalog.query import Contains
from repoze.catalog.query import Name
from repoze.catalog.query import Any
from pyramid.traversal import resource_path
from pyramid.traversal import find_resource

from arche.views.base import BaseView
from arche import security
from arche import _


SEARCH_VIEW_QUERY = Eq('path', Name('path')) & Contains('searchable_text', Name('searchable_text'))


class SearchView(BaseView):

    def __call__(self):
        self.docids = ()
        query = self.request.GET.get('query', None)
        if query:
            path = resource_path(self.context)
            query_vals = {'searchable_text': query,
                          'path': path}
            self.docids = self.root.catalog.query(SEARCH_VIEW_QUERY,
                                                  names = query_vals)[1]
        return {'results': self.result_objects()}

    def result_objects(self):
        for docid in self.docids:
            path = self.root.document_map.address_for_docid(docid)
            obj = find_resource(self.root, path)
            if self.request.has_permission(security.PERM_VIEW, obj):
                yield obj


def includeme(config):
    config.add_view(SearchView,
                    name = 'search',
                    permission = security.PERM_VIEW, #FIXME
                    renderer = "arche:templates/search.pt",
                    context = 'arche.interfaces.IRoot')

