import random
import string

import deform
from colander import null
from deform.compat import uppercase
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.response import Response

from arche.views.base import DefaultAddForm
from arche.views.base import BaseView
from arche import security
from arche.schemas import AddFileSchema
from arche.utils import FileUploadTempStore
from arche.utils import get_content_factories
from arche.utils import generate_slug
from arche import _


class AddLinkForm(DefaultAddForm):
    type_name = u"Link"
    
    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        name = appstruct.pop('name')
        factory = self.get_content_factory(self.type_name)
        obj = factory(**appstruct)
        #name = generate_slug(self.context, obj.filename)
        self.context[name] = obj
        return HTTPFound(location = self.request.resource_url(obj))


class LinkView(BaseView):

    def __call__(self):
        #check perm, if edit, show view otherwise redirect
        if self.request.has_permission(security.PERM_EDIT):
            return {}
        elif self.context.target:
            return HTTPFound(location = self.context.target)
        raise HTTPForbidden("You're not allowed to view this context.")


def includeme(config):
    config.add_view(AddLinkForm,
                    context = 'arche.interfaces.IContent',
                    name = 'add',
                    request_param = "content_type=Link",
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_view(LinkView,
                    context = 'arche.interfaces.ILink',
                    renderer = 'arche:templates/content/link.pt',
                    permission = security.NO_PERMISSION_REQUIRED,) #Selected by that view
