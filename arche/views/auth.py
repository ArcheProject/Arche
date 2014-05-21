import deform
from pyramid.security import remember
from pyramid.security import forget
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden

from arche.views.base import BaseForm
from arche.interfaces import IRoot
from arche.utils import send_email
from arche import security
from arche import _


class LoginForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'login'

    @property
    def buttons(self):
        return (deform.Button('login', title = _(u"Login"), css_class = 'btn btn-primary'),
                deform.Button('recover', title = _(u"Recover password"), css_class = 'btn btn-primary'),
                self.button_cancel,)

    def recover_success(self, appstruct):
        return HTTPFound(location = self.request.resource_url(self.root, 'recover_password'))
    recover_failed = recover_success

    def login_success(self, appstruct):
        self.flash_messages.add(_(u"Welcome!"), type="success")
        email_or_userid = appstruct['email_or_userid']
        if '@' in email_or_userid:
            user = self.context['users'].get_user_by_email(email_or_userid)
        else:
            user = self.context['users'].get(email_or_userid, None)
        if user is None:
            raise HTTPForbidden("Something went wrong during login. No user profile found.")
        headers = remember(self.request, user.userid)
        #FIXME: Came from?
        return HTTPFound(location = self.request.application_url, headers = headers)


class RegisterForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'register'

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


class RecoverPasswordForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'recover_password'

    @property
    def buttons(self):
        return (deform.Button('send', title = _(u"Send"), css_class = 'btn btn-primary'),
                 self.button_cancel,)

    def send_success(self, appstruct):
        self.flash_messages.add(_(u"Message sent"), type="success")
        factory = self.get_content_factory(u'Token')
        email_or_userid = appstruct['email_or_userid']
        if '@' in email_or_userid:
            user = self.context['users'].get_user_by_email(email_or_userid)
        else:
            user = self.context['users'].get(email_or_userid, None)
        if user is None:
            raise HTTPForbidden("Something went wrong during login. No user profile found.")
        user.pw_token = factory()
        html = self.render_template("arche:templates/emails/recover_password.pt", user = user)
        print html
        send_email(_(u"Password recovery request"),
                   [user.email],
                   html,
                   request = self.request)
        return HTTPFound(location = self.request.resource_url(self.root))

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
    config.add_view(RecoverPasswordForm,
                    context = IRoot,
                    name = 'recover_password',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_view(logout,
                    context = IRoot,
                    name = 'logout',
                    permission = security.NO_PERMISSION_REQUIRED)
