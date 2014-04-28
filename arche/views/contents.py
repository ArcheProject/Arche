from arche.interfaces import IFolder
from arche.views.base import BaseView
from arche import security
from arche import _
from arche.fanstatic_lib import dropzonejs

class ContentsView(BaseView):

    def __call__(self):
        dropzonejs.need()
        if IFolder.providedBy(self.context):
            return {'contents': self.context.values()}
        return {'contents': ()}


def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IContent')
