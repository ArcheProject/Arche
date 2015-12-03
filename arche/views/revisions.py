from arche.views.base import BaseView
from arche.interfaces import IRevisions
from arche.interfaces import ITrackRevisions
from arche.security import PERM_MANAGE_SYSTEM


class RevisionsView(BaseView):
    """ Show generic revision/versioning information.
        Maybe not very usable in most cases. Use a specific
        implementation related to a specific field instead.
    """

    def __call__(self):
        revisions = IRevisions(self.context, None)
        response = {'revisions': revisions, 'possible_attrs': (), 'review_attr': None}
        if revisions:
            possible_attrs = revisions.get_tracked_attributes(self.request.registry)
            response['possible_attrs'] = possible_attrs
            if self.request.subpath:
                review_attr = self.request.subpath[0]
                if review_attr in possible_attrs:
                    response['review_attr'] = review_attr
        return response


def includeme(config):
    config.add_view(RevisionsView,
                    context = ITrackRevisions,
                    name = '__revisions__',
                    permission = PERM_MANAGE_SYSTEM,
                    renderer = 'arche:templates/revisions.pt')
