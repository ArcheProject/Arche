import datetime

from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response

from arche.views.base import DefaultView
from arche import security
from arche.interfaces import IThumbnails
from arche.utils import get_image_scales
from arche.views.file import AddFileForm
from arche.views.file import download_view
from arche.views.file import inline_view


class AddImageForm(AddFileForm):
    type_name = u"Image"


def thumb_view(context, request, subpath = None):
    if subpath is None:
        subpath = request.subpath
    if len(subpath) not in (2, 3):
        return HTTPNotFound()
    key = subpath[0] #Usually 'image', the blob area where it's stored
    scale_name = subpath[1] #Some scale, like 'col-1'
    try:
        direction = subpath[2]
    except IndexError:
        #Old API - keep this around
        direction = request.GET.get('direction', 'thumbnail')
    scales = get_image_scales()
    if scale_name not in scales:
        return HTTPNotFound()
    thumbnails = request.registry.queryAdapter(context, IThumbnails)
    if not thumbnails:
        #Log?
        raise HTTPNotFound()
    thumb = thumbnails.get_thumb(scale_name, key = key, direction = direction)
    if thumb:
        return Response(
            body = thumb.image,
            headerlist=[
                ('Content-Type', thumb.mimetype),
                ('Etag', thumb.etag)
                ]
            )
    raise HTTPNotFound()


def includeme(config):
    config.add_view(AddImageForm,
                    context = 'arche.interfaces.IContent',
                    name = 'add',
                    request_param = "content_type=Image",
                    permission = security.NO_PERMISSION_REQUIRED, #FIXME: perm check in add
                    renderer = 'arche:templates/form.pt')
    config.add_view(DefaultView,
                    context = 'arche.interfaces.IImage',
                    permission = security.PERM_VIEW,
                    renderer = 'arche:templates/content/image.pt') #FIXME: View
    config.add_view(download_view,
                    context = 'arche.interfaces.IImage',
                    permission = security.PERM_VIEW,
                    name = 'download')
    config.add_view(thumb_view,
                    http_cache = datetime.timedelta(days=1),
                    name = 'thumbnail',
                    context = 'arche.interfaces.IThumbnailedContent',
                    permission = security.PERM_VIEW)
    config.add_view(inline_view,
                    http_cache = datetime.timedelta(days=1),
                    name = 'inline',
                    context = 'arche.interfaces.IThumbnailedContent',
                    permission = security.PERM_VIEW)
