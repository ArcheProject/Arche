from arche.views.base import BaseView
from arche import security
from arche import _


class ContentsView(BaseView):

    def __call__(self):
        return {'contents': self.context.values()}


def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IContent')
