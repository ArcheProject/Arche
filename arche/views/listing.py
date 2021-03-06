from arche.views.base import ContentView
from arche import security
from arche import _


class ListingView(ContentView):
    title = _('Content listing')

    def __call__(self):
        return {'contents': [x for x in self.context.values() if getattr(x, 'listing_visible', False)]}


def includeme(config):
    config.add_view(ListingView,
                    name = 'listing_view',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = "arche:templates/content/listing_view.pt",
                    context = 'arche.interfaces.IBase')
    config.add_content_view('Document', 'listing_view', ListingView)
    config.add_content_view('Root', 'listing_view', ListingView)
