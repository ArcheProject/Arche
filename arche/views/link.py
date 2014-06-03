from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound

from arche import _
from arche import security
from arche.views.base import BaseView
from arche.views.base import DefaultAddForm


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
