from arche.interfaces import IFolder
from arche.views.base import BaseView

from arche import security
from arche import _

#from arche.fanstatic_lib import dropzonejs


class ContentsView(BaseView):

    def __call__(self):
#        dropzonejs.need()
        is_folderish = IFolder.providedBy(self.context)
        response = {'is_folderish': is_folderish, 'contents': ()}
        if is_folderish:
            response['contents'] = self.context.values()
        return response


def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IContent')
