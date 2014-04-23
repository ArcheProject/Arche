from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from arche.views.base import DefaultView
from arche import security
from arche.utils import IThumbnails
from arche.utils import get_image_scales
from arche.views.file import (AddFileForm,
                              file_data_response,
                              download_view,
                              inline_view)
from arche import _


class AddImageForm(AddFileForm):
    type_name = u"Image"


def thumb_view(context, request, subpath = None):
    if subpath is None:
        subpath = request.subpath
    #FIXME: Default sizes etc?
    if subpath:
        scale_name = subpath[0]
    else:
        scale_name = u"col-1" #???
    scales = get_image_scales()
    if scale_name not in scales:
        return HTTPNotFound()
    thumbnails = request.registry.queryAdapter(context, IThumbnails)
    if not thumbnails:
        #Log?
        raise HTTPNotFound()
    thumb = thumbnails.get_thumb(scale_name)
    if thumb:
        return Response(
            body = thumb.image,
            headerlist=[
                    #     disposition = 'inline'
               # ('Content-Disposition', '%s;filename="%s"' % (
               #     disposition, context.filename.encode('ascii', 'ignore'))),
                ('Content-Type', thumb.mimetype),
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
    config.add_view(inline_view,
                    context = 'arche.interfaces.IImage',
                    permission = security.PERM_VIEW,
                    name = 'view')
    config.add_view(thumb_view,
                    name = 'thumbnail',
                    context = 'arche.interfaces.IThumbnailedContent',
                    permission = security.PERM_VIEW)