from arche.interfaces import IJSONData
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.httpexceptions import HTTPBadRequest
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


def logic_wrap(word):
    if word in ('and', 'or'):
        return '"{}"'.format(word)
    return word


@view_defaults(permission = security.PERM_VIEW, context = 'arche.interfaces.IRoot')
class SearchView(BaseView):
    result = None

    @reify
    def limit(self):
        limit = self.request.params.get('limit', 15)
        try:
            limit = int(limit)
        except TypeError:
            limit = 15
        return limit

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
            if '"' not in query:
                query = ' '.join(logic_wrap(word) for word in query.split())
            query_objs.append(Contains('searchable_text', query))
            perform_query = True
        #Check other get-values:
        #FIXME: This should be smarter, and should perhaps be able to handle glob, other types of queries etc.
        for (k, v) in self.request.GET.mixed().items():
            if v and k in self.root.catalog:
                perform_query = True
                if isinstance(v, string_types):
                    if v.isdigit():
                        query_objs.append(Eq(k, int(v)) | Eq(k, v))
                    else:
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
            #Limit kw is only used by the catalog if a sort index is specified
            self.result, self.docids = self.root.catalog.query(query_obj)
        except ParseError:
            if not self.request.is_xhr:
                msg = _(u"Invalid search query - try something else!")
                self.flash_messages.add(msg, type="danger")

    @view_config(name = 'search', renderer = 'arche:templates/search.pt')
    def search_page(self):
        self._mk_query()
        return {'results': tuple(self.resolve_docids(self.docids)),
                'total': self.result and self.result.total or 0,
                'query': self.request.GET.get('query', ''),}

    @view_config(name = 'search.json', renderer = 'json')
    def search_json(self):
        self._mk_query()
        scale = self.request.params.get('scale', 'mini')
        output = []
        limit = self.limit
        for obj in self.resolve_docids(self.docids):
            if limit > 0:
                try:
                    thumb_url = self.request.thumb_url(obj, scale)
                except AttributeError:
                    thumb_url = ''
                json_data = IJSONData(obj)
                item = json_data(self.request, dt_formater=self.request.dt_handler.format_dt)
                item['thumb_url'] = thumb_url
                item['url'] = self.request.resource_url(obj)
                output.append(item)
                limit -= 1
        total = self.result and self.result.total or 0
        response = {'results': output, 'total': total}
        if total == 0:
            response['msg'] = self.request.localizer.translate(_("No results"))
        elif total > self.limit:
            msg = _("${num} more results...",
                    mapping = {'num': total - self.limit})
            response['msg'] = self.request.localizer.translate(msg)
        return response

    @view_config(name = 'search_select2.json', renderer = 'json')
    def search_select_2_json(self):
        id_attr = self.request.GET.pop('id_attr', 'uid')
        if id_attr not in ('uid', 'userid'):
            raise HTTPBadRequest()
        self._mk_query()
        output = []
        for obj in self.resolve_docids(self.docids):
            type_title = getattr(obj, 'type_title', getattr(obj, 'type_name', "(Unknown)"))
            if isinstance(type_title, TranslationString):
                type_title = self.request.localizer.translate(type_title)
            try:
                tag = self.request.thumb_tag(obj, 'mini')
            except AttributeError:
                tag = ''
            user_extra = id_attr == 'userid' and ' ({})'.format(obj.userid) or ''
            output.append({'text': obj.title + user_extra,
                           'id': getattr(obj, id_attr),
                           'type_name': obj.type_name,
                           'img_tag': tag,
                           'type_title': '' if user_extra else type_title})
        return {'results': output}

    @view_config(route_name='resolve_uid')
    def redirect_resolve_uid(self):
        obj = self.request.resolve_uid(self.request.matchdict['uid'])
        if obj:
            url = self.request.resource_url(obj)
            return HTTPFound(location=url)
        raise HTTPNotFound()


def includeme(config):
    config.add_route('resolve_uid', '/_resolve_uid/{uid}')
    config.scan('.search')
