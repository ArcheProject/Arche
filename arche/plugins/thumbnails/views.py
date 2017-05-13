import datetime

from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response

from arche import _
from arche import security
from arche.interfaces import IArcheFolder
from arche.interfaces import IThumbnails
from arche.security import PERM_VIEW
from arche.utils import get_image_scales
from arche.views.base import ContentView


def thumb_view(context, request, subpath=None):
    if subpath is None:
        subpath = request.subpath
    if len(subpath) not in (2, 3):
        return HTTPNotFound()
    key = subpath[0]  # Usually 'image', the blob area where it's stored
    scale_name = subpath[1]  # Some scale, like 'col-1'
    try:
        direction = subpath[2]
    except IndexError:
        # Old API - keep this around
        direction = request.GET.get('direction', 'thumbnail')
    scales = get_image_scales()
    if scale_name not in scales:
        return HTTPNotFound()
    thumbnails = request.registry.queryAdapter(context, IThumbnails)
    if not thumbnails:
        # Log?
        raise HTTPNotFound()
    thumb = thumbnails.get_thumb(scale_name, key=key, direction=direction)
    if thumb:
        return Response(
            body=thumb.image,
            headerlist=[
                ('Content-Type', thumb.mimetype),
                ('Etag', thumb.etag)
            ]
        )
    raise HTTPNotFound()


class AlbumView(ContentView):
    """ Use this for more complex views that can have settings and be dynamically selected
        as a view for content types
    """
    title = _("Album view")
    description = _("Photo album-like view")

    def __call__(self):
        return {}


def includeme(config):
    config.add_view(
        thumb_view,
        http_cache=datetime.timedelta(days=1),
        name='thumbnail',
        context='arche.interfaces.IThumbnailedContent',
        permission=security.PERM_VIEW)
    config.add_view(
        AlbumView,
        context=IArcheFolder,
        name='album_view',
        permission=PERM_VIEW,
        renderer="arche:templates/content/folder_album.pt")
    config.add_content_view('Folder', 'album_view', AlbumView)
