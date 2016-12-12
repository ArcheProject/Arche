""" Folderish views, suitable for folders, root or similar. """
from pyramid.view import view_config

from arche.interfaces import IArcheFolder
from arche.security import PERM_VIEW
from arche.views.base import ContentView
from arche import _


@view_config(context=IArcheFolder,
             name='album_view',
             permission=PERM_VIEW,
             renderer="arche:templates/content/folder_album.pt")
class AlbumView(ContentView):
    """ Use this for more complex views that can have settings and be dynamically selected
        as a view for content types
    """
    title = _("Album view")
    description = _("Photo album-like view")

    def __call__(self):
        return {}


def includeme(config):
    config.scan(__name__)
    config.add_content_view('Folder', 'album_view', AlbumView)
