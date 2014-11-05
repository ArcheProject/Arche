from peppercorn import parse

from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.decorator import reify

from arche import _
from arche import security
from arche.fanstatic_lib import jqueryui
from arche.fanstatic_lib import touchpunch_js
from arche.fanstatic_lib import pure_js
from arche.interfaces import IJSONData
from arche.interfaces import IDateTimeHandler
from arche.interfaces import IFolder
from arche.views.base import BaseView
from pyramid.traversal import find_interface


class ContentsView(BaseView):

    def __call__(self):
        jqueryui.need()
        touchpunch_js.need()
        pure_js.need()
        return {'is_folderish': IFolder.providedBy(self.context)}


class SortedView(BaseView):

    def __call__(self):
        content_keys = self.request.POST.getall('content_name')
        keys = set(self.context.keys())
        for item in content_keys:
            if item not in keys:
                return HTTPForbidden("You tried to set a value that doesn't exist.")
            keys.remove(item)
        content_keys.extend(keys)
        self.context.order = content_keys
        return HTTPFound(location = self.request.resource_url(self.context))


class JSONContents(BaseView):
    """ Batch get generic object data. Good for listings and similar. """

    @reify
    def dt_handler(self):
        return IDateTimeHandler(self.request)

    def __call__(self):
        response = {}
        action = self.request.POST.get('action', None)
        if  action == 'delete':
            for item in self.request.POST.getall('select'):
                obj = self.context.get(item)
                if self.request.has_permission(security.PERM_DELETE, obj) and self.root != obj and not hasattr(obj, 'is_permanent'):
                    del self.context[item]
        results = []
        for obj in self.context.values():
            if self.request.has_permission(security.PERM_VIEW, obj):
                results.append(obj)
        
        response['items'] = self.json_format_objects(results)
        return response

    def json_format_objects(self, items):
        res = []
        for obj in items:
            adapted = IJSONData(obj)
            result = adapted(self.request, dt_formater = self.dt_handler.format_relative)
            if result.get('size', None):
                result['size'] = "%s %s" % self.byte_format(result['size'])
            res.append(result)
        return res


def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IContent')
    config.add_view(SortedView,
                    name = 'sorted',
                    permission = security.PERM_EDIT,
                    context = 'arche.interfaces.IFolder')
    config.add_view(JSONContents,
                    name = 'contents.json',
                    permission = security.PERM_VIEW,
                    renderer = "json",
                    context = 'arche.interfaces.IContent')
