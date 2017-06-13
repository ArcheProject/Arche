import datetime

from arche.views.base import DefaultView
from arche import security
from arche.views.file import AddFileForm
from arche.views.file import download_view
from arche.views.file import inline_view


class AddImageForm(AddFileForm):
    type_name = u"Image"


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
    #Note: The inline view doesn't require something to have thumbnail - it's supposed to be the
    #Original image
    config.add_view(inline_view,
                    http_cache = datetime.timedelta(days=1),
                    name = 'inline',
                    context = 'arche.interfaces.IThumbnailedContent',
                    permission = security.PERM_VIEW)
