import deform
from pyramid.security import remember
from pyramid.security import forget
from pyramid.httpexceptions import HTTPFound

from arche.views.base import BaseForm
from arche.interfaces import IRoot
from arche import security
from arche import _


class LoginForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'login'
    heading = _("Login")

    @property
    def buttons(self):
        #FIXME: Forgot password here!
        return (deform.Button('login', title = _(u"Login"), css_class = 'btn btn-primary'),
                self.button_cancel,)

    def login_success(self, appstruct):
        self.flash_messages.add(_(u"Welcome!"), type="success")
        user = self.root['users'].get_user_by_email(appstruct['email'])
        headers = remember(self.request, user.userid)
        #FIXME: Came from?
        return HTTPFound(location = self.request.application_url, headers = headers)


class RegisterForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'register'
    heading = _("Register")

    @property
    def buttons(self):
        return (deform.Button('register', title = _(u"Register"), css_class = 'btn btn-primary'),
                 self.button_cancel,)

    def register_success(self, appstruct):
        self.flash_messages.add(_(u"Welcome, you're now registered!"), type="success")
        factory = self.get_content_factory(u'User')
        userid = appstruct.pop('userid')
        obj = factory(**appstruct)
        self.context['users'][userid] = obj
        headers = remember(self.request, obj.userid)
        return HTTPFound(location = self.request.resource_url(obj), headers = headers)

def logout(context, request):
    headers = forget(request)
    return HTTPFound(location = request.resource_url(context),
                     headers = headers)


def includeme(config):
    config.add_view(LoginForm,
                    context = IRoot,
                    name = 'login',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_view(RegisterForm,
                    context = IRoot,
                    name = 'register',
                    permission = security.PERM_REGISTER,
                    renderer = 'arche:templates/form.pt')
    config.add_view(logout,
                    context = IRoot,
                    name = 'logout',
                    permission = security.NO_PERMISSION_REQUIRED)
