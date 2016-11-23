from pyramid.httpexceptions import HTTPForbidden

from arche import security
from arche.fanstatic_lib import touchpunch_js
from arche.fanstatic_lib import folderish_contents_js
from arche.interfaces import IJSONData
from arche.interfaces import IFolder
from arche.views.base import BaseView


class ContentsView(BaseView):

    def __call__(self):
        folderish_contents_js.need()
        touchpunch_js.need()
        addable_types = set([x.type_name for x in self.addable_content(self.context)])
        show_upload = bool(set(['File', 'Image']) & addable_types)
        return {'is_folderish': IFolder.providedBy(self.context), 'show_upload': show_upload}


class JSONContents(BaseView):
    """ Batch get generic object data. Good for listings and similar. """

    def __call__(self):
        response = {}
        action = self.request.POST.get('action', None)
        if action == 'delete':
            for item in self.request.POST.getall('select'):
                obj = self.context.get(item)
                if self.request.has_permission(security.PERM_DELETE, obj) and self.root != obj and not getattr(obj, 'is_permanent', False):
                    del self.context[item]
        if action == 'sort':
            content_keys = self.request.POST.getall('content_name')
            keys = set(self.context.keys())
            for item in content_keys:
                if item not in keys:
                    return HTTPForbidden("You tried to set a value that doesn't exist.")
                keys.remove(item)
            content_keys.extend(keys)
            self.context.order = content_keys
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
            result = adapted(self.request, dt_formater = self.request.dt_handler.format_relative)
            if result.get('size', None):
                result['size'] = "%s %s" % self.byte_format(result['size'])
            res.append(result)
        return res


def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.PERM_EDIT,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IContent')
    config.add_view(JSONContents,
                    name = 'contents.json',
                    permission = security.PERM_EDIT,
                    renderer = "json",
                    context = 'arche.interfaces.IContent')
