import random
import string

import deform
from deform.compat import uppercase
from pyramid.httpexceptions import HTTPFound, HTTPNotFound
from pyramid.response import Response
from pyramid.view import render_view_to_response

from arche.views.base import DefaultAddForm
from arche.views.base import DefaultView
from arche import security
from arche.schemas import AddFileSchema
from arche.utils import FileUploadTempStore, get_mimetype_views
from arche.utils import get_content_factories
from arche.utils import generate_slug
from arche.interfaces import IBlobs
from arche import _



class AddFileForm(DefaultAddForm):
    type_name = u"File"
    
    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        obj = factory(**appstruct)
        name = generate_slug(self.context, obj.filename)
        self.context[name] = obj
        return HTTPFound(location = self.request.resource_url(obj))


def file_data_response(context, request, disposition = 'inline'):
    res = Response(
        headerlist=[
            ('Content-Disposition', '%s;filename="%s"' % (
                disposition, context.filename.encode('ascii', 'ignore'))),
            ('Content-Type', str(context.mimetype)),
            ]
        )
    #Should this be fault tolerant in some way?
    with IBlobs(context)['file'].blob.open() as f:
        res.body = f.read()
    return res

def download_view(context, request):
    return file_data_response(context, request, disposition = 'attachment')

def inline_view(context, request):
    return file_data_response(context, request, disposition = 'inline')

def batch_file_upload_handler_view(context, request):
    controls = request.params.items()
    controls.insert(0, ('__start__', 'file_data:mapping'))
    controls.append(('__end__', 'file_data:mapping'))
    schema = AddFileSchema()
    schema = schema.bind(request = request, context = context)
    form = deform.Form(schema)
    appstruct = form.validate(controls)
    factory = get_content_factories()['File']
    obj = factory(**appstruct)
    name = generate_slug(context, obj.filename)
    context[name] = obj
    return Response()

def upload_temp(context, request):
    upload = request.params['upload']
    uid = None
    tmpstore = FileUploadTempStore(request)
    
    if hasattr(upload, 'file'):
        # the upload control had a file selected
        data = dict()
        data['fp'] = upload.file
        filename = upload.filename
        # sanitize IE whole-path filenames
        filename = filename[filename.rfind('\\')+1:].strip()
        data['filename'] = filename
        data['mimetype'] = upload.type
        data['size']  = upload.length
        while 1:
            uid = ''.join([random.choice(uppercase+string.digits) for i in range(10)])
            if tmpstore.get(uid) is None:
                data['uid'] = uid
                tmpstore[uid] = data
                preview_url = tmpstore.preview_url(uid)
                tmpstore[uid]['preview_url'] = preview_url
                break
    return {'uid':uid}


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
    config.add_view(batch_file_upload_handler_view,
                    context = 'arche.interfaces.IContent',
                    permission = security.PERM_VIEW,
                    name = 'upload')
    config.add_view(upload_temp,
                    context = 'arche.interfaces.IContent',
                    permission = security.PERM_VIEW,
                    name = 'upload_temp',
                    renderer = 'json')
