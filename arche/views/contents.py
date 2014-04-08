from arche.views.base import BaseView
from arche import security
from arche import _


class ContentsView(BaseView):

    def __call__(self):
        return {'contents': self.context.values()}


def includeme(config):
    config.add_view(ContentsView,
                    name = 'contents',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = "arche:templates/contents.pt",
                    context = 'arche.interfaces.IBase')
