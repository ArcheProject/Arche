from pyramid.httpexceptions import HTTPFound, HTTPNotFound

from arche.interfaces import IFolder
from arche.views.base import BaseView

from arche import security
from arche import _
from arche.fanstatic_lib import jqueryui, touchpunch_js

class ContentsView(BaseView):

    def __call__(self):
        jqueryui.need()
        touchpunch_js.need()
        is_folderish = IFolder.providedBy(self.context)
        response = {'is_folderish': is_folderish, 'contents': ()}
        if is_folderish:
            response['contents'] = self.context.values()
        return response
    

class SortedView(BaseView):

    def __call__(self):
        content_keys = self.request.POST.getall('content_name')
        keys = set(self.context.keys())
        for item in content_keys:
            if item not in keys:
                return HTTPNotFound()
            keys.remove(item)
        content_keys.extend(keys)
        self.context.order = content_keys
        return HTTPFound(location = self.request.resource_url(self.context))

def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IContent')
    config.add_view(SortedView,
                    name = 'sorted',
                    permission = security.PERM_EDIT,
                    context = 'arche.interfaces.IContent')
