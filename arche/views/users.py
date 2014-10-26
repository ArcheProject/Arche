from __future__ import unicode_literals

from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden
from pyramid.decorator import reify

from arche import _
from arche import security
from arche.fanstatic_lib import pure_js
from arche.interfaces import IDateTimeHandler
from arche.interfaces import IJSONData
from arche.views.base import BaseView
from arche.views.base import DefaultAddForm
from arche.views.base import DefaultEditForm


class UserAddForm(DefaultAddForm):
    type_name = 'User'

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        userid = appstruct.pop('userid')
        obj = factory(**appstruct)
        self.context[userid] = obj
        return HTTPFound(location = self.request.resource_url(obj))


class UserChangePasswordForm(DefaultEditForm):
    type_name = 'User'
    schema_name = 'change_password'

    def __init__(self, context, request):
        if request.authenticated_userid is None:
            token = getattr(context, 'pw_token', None)
            rtoken = request.GET.get('t', object())
            if token == rtoken and token.valid:
                super(UserChangePasswordForm, self).__init__(context, request)
                return
        else:
            if request.has_permission(security.PERM_EDIT):
                super(UserChangePasswordForm, self).__init__(context, request)
                return
        raise HTTPForbidden(_("Not allowed"))

    def save_success(self, appstruct):
        if getattr(self.context, 'pw_token', None) is not None:
            self.context.pw_token = None
        #This is the only thing that should ever be changed here!
        self.context.update(password = appstruct['password'])
        self.flash_messages.add(_("Password changed"))
        if self.request.authenticated_userid:
            return HTTPFound(location = self.request.resource_url(self.context))
        return HTTPFound(location = self.request.resource_url(self.root, 'login'))


class UsersView(BaseView):
    """ A table listing of all users.
    """

    def __call__(self):
        pure_js.need()
        return {}


class JSONUsers(BaseView):

    @reify
    def dt_handler(self):
        return IDateTimeHandler(self.request)

    def __call__(self):
        results = []
        for obj in self.context.values():
            if self.request.has_permission(security.PERM_VIEW, obj):
                results.append(obj)
        response = {}
        response['items'] = self.json_format_objects(results)
        return response

    def json_format_objects(self, items):
        res = []
        for obj in items:
            adapted = IJSONData(obj)
            res.append(adapted(self.request, dt_formater = self.dt_handler.format_relative, attrs = ('userid', 'email', 'first_name', 'last_name')))
        return res


class UserView(BaseView):

    def __call__(self):
        return {}


def includeme(config):
    config.add_view(UserAddForm,
                    context = 'arche.interfaces.IUsers',
                    name = 'add',
                    request_param = "content_type=User",
                    permission = security.PERM_MANAGE_USERS, #FIXME: Not add user perm?
                    renderer = 'arche:templates/form.pt')
    config.add_view(UserChangePasswordForm,
                    context = 'arche.interfaces.IUser',
                    name = 'change_password',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_view(UsersView,
                    name = 'view',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "arche:templates/content/users_table.pt",
                    context = 'arche.interfaces.IUsers')
    config.add_view(JSONUsers,
                    name = 'users.json',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "json",
                    context = 'arche.interfaces.IUsers')
    config.add_view(UserView,
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/content/user.pt",
                    context = 'arche.interfaces.IUser')
