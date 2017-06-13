import deform
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
from pyramid.response import Response
from pyramid.view import render_view_to_response

from arche import security
from arche.interfaces import IBlobs
from arche.schemas import AddFileSchema
from arche.utils import generate_slug
from arche.utils import image_mime_to_title
from arche.utils import get_mimetype_views
from arche.views.base import DefaultAddForm
from arche.views.base import DefaultView
from arche.views.contents import JSONContents


class AddFileForm(DefaultAddForm):
    type_name = u"File"
    
    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        obj = factory(**appstruct)
        name = generate_slug(self.context, obj.filename)
        self.context[name] = obj
        return HTTPFound(location = self.request.resource_url(obj))


def file_data_response(context, request, disposition = 'inline', blob_key = None):
    filename = getattr(context, 'filename', context.uid).encode('ascii', 'ignore')
    if blob_key is None:
        blob_key = getattr(context, 'blob_key', 'file')
    body = None
    mimetype = ""
    try:
        blobfile = IBlobs(context)[blob_key]
        with blobfile.blob.open() as f:
            body = f.read()
        mimetype = blobfile.mimetype
    except KeyError:
        pass
    if not body:
        raise HTTPNotFound("No such key")
    headerslist = [
        ('Content-Disposition', '%s;filename="%s"' % (
            disposition, filename)),
        ('Content-Type', str(mimetype)),
    ]
    return Response(headerlist=headerslist, body=body)


def download_view(context, request):
    return file_data_response(context, request, disposition = 'attachment')


def inline_view(context, request):
    return file_data_response(context, request, disposition = 'inline')


#FIXME: This reloads all content when something is uploaded. Pretty silly.
class BatchFileUploadView(JSONContents):

    def __call__(self):
        controls = self.request.params.items()
        controls.insert(0, ('__start__', 'file_data:mapping'))
        controls.append(('__end__', 'file_data:mapping'))
        schema = AddFileSchema()
        schema = schema.bind(request = self.request, context = self.context, view = self)
        form = deform.Form(schema)
        try:
            appstruct = form.validate(controls)
        except Exception as exc:
            raise HTTPForbidden("Validation error")
        addable_factories = dict([(x.type_name, x) for x in self.addable_content(self.context)])
        factory = None
        if appstruct['file_data']['mimetype'] in image_mime_to_title:
            factory = addable_factories.get('Image', None)
        else:
            factory = addable_factories.get('File', None)
        if not factory:
            raise HTTPForbidden("You can't upload this type here")
        obj = factory(**appstruct)
        name = generate_slug(self.context, obj.filename)
        self.context[name] = obj
        return super(BatchFileUploadView, self).__call__()


# def upload_temp(context, request):
#     upload = request.params['upload']
#     uid = None
#     tmpstore = FileUploadTempStore(request)
#
#     if hasattr(upload, 'file'):
#         # the upload control had a file selected
#         data = dict()
#         data['fp'] = upload.file
#         filename = upload.filename
#         # sanitize IE whole-path filenames
#         filename = filename[filename.rfind('\\')+1:].strip()
#         data['filename'] = filename
#         data['mimetype'] = upload.type
#         data['size']  = upload.length
#         while 1:
#             uid = ''.join([random.choice(uppercase+string.digits) for i in range(10)])
#             if tmpstore.get(uid) is None:
#                 data['uid'] = uid
#                 tmpstore[uid] = data
#                 preview_url = tmpstore.preview_url(uid)
#                 tmpstore[uid]['preview_url'] = preview_url
#                 break
#     return {'uid':uid}


def mimetype_view_selector(context, request):
    mime_views = get_mimetype_views(request.registry)
    name = mime_views.get(context.mimetype, 'view')
    response = render_view_to_response(context, request, name = name)
    if response is None:
        raise HTTPNotFound()
    return response


def includeme(config):
    config.add_view(AddFileForm,
                    context = 'arche.interfaces.IContent',
                    name = 'add',
                    request_param = "content_type=File",
                    permission = security.NO_PERMISSION_REQUIRED, #FIXME: perm check in add
                    renderer = 'arche:templates/form.pt')
    config.add_view(mimetype_view_selector,
                    context = 'arche.interfaces.IFile',
                    permission = security.NO_PERMISSION_REQUIRED)
    config.add_view(DefaultView,
                    name = 'view',
                    context = 'arche.interfaces.IFile',
                    permission = security.PERM_VIEW,
                    renderer = 'arche:templates/content/file.pt')
    config.add_view(download_view,
                    context = 'arche.interfaces.IFile',
                    permission = security.PERM_VIEW,
                    name = 'download')
    config.add_view(inline_view,
                    context = 'arche.interfaces.IFile',
                    permission = security.PERM_VIEW,
                    name = 'inline')
    config.add_view(BatchFileUploadView,
                    context = 'arche.interfaces.IContent',
                    permission = security.PERM_VIEW,
                    name = 'upload',
                    renderer = 'json')
    # config.add_view(upload_temp,
    #                 context = 'arche.interfaces.IContent',
    #                 permission = security.PERM_VIEW,
    #                 name = 'upload_temp',
    #                 renderer = 'json')
