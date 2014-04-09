from pyramid.httpexceptions import HTTPFound
from pyramid.response import Response

from arche.views.base import DefaultAddForm
from arche.views.base import DefaultView
from arche import security
from arche.utils import generate_slug
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
    with context.blobfile.open() as f:
        res.body = f.read()
    return res

def download_view(context, request):
    return file_data_response(context, request, disposition = 'attachment')

def inline_view(context, request):
    return file_data_response(context, request, disposition = 'inline')


def includeme(config):
    config.add_view(AddFileForm,
                    context = 'arche.interfaces.IContent',
                    name = 'add',
                    request_param = "content_type=File",
                    permission = security.NO_PERMISSION_REQUIRED, #FIXME: perm check in add
                    renderer = 'arche:templates/form.pt')
    config.add_view(DefaultView,
                    context = 'arche.interfaces.IFile',
                    permission = security.PERM_VIEW,
                    renderer = 'arche:templates/file.pt')
    config.add_view(download_view,
                    context = 'arche.interfaces.IFile',
                    permission = security.PERM_VIEW,
                    name = 'download')
    config.add_view(inline_view,
                    context = 'arche.interfaces.IFile',
                    permission = security.PERM_VIEW,
                    name = 'view')

