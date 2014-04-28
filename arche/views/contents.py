from arche.interfaces import IFolder
from arche.views.base import BaseView
from arche import security
from arche import _


class ContentsView(BaseView):

    def __call__(self):
        if IFolder.providedBy(self.context):
            return {'contents': self.context.values()}
        return {'contents': ()}


def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IContent')
