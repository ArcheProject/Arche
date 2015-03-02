from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget
from pyramid.security import remember
import deform

from arche import _
from arche import security
from arche.interfaces import IRegistrationTokens
from arche.interfaces import IRoot
from arche.utils import send_email
from arche.views.base import BaseForm
from pyramid.response import Response


class LoginForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'login'
    title = _(u"Login")
    use_ajax = True
    formid = 'login-form'

    @property
    def buttons(self):
        return (deform.Button('login', title = _(u"Login"), css_class = 'btn btn-primary'),
                deform.Button('recover', title = _(u"Recover password"), css_class = 'btn btn'),
                self.button_cancel,)

    def recover_success(self, appstruct):
        if self.request.is_xhr:
            url = self.request.resource_url(self.root, 'recover_password', query = {'modal': 'recover_password'})
            return Response("""<script type="text/javascript">
                arche.create_modal('recover_password', '%s');
                </script>""" % url)
        url = self.request.resource_url(self.root, 'recover_password')
        return HTTPFound(location = url)
    recover_failure = recover_success

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
        url  = appstruct.pop('came_from', None)
        return self.relocate_response(url, headers = headers)


class RegisterForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'register'
    title = _(u"Register")

    def __init__(self, context, request):
        super(RegisterForm, self).__init__(context, request)
        if request.authenticated_userid:
            msg = _("Already logged in.")
            self.flash_messages.add(msg, type = 'danger')
            raise HTTPFound(location = request.resource_url(context))
        elif context.site_settings.get('allow_self_registration'):
            return #Ie allowed
        msg = _("This site doesn't allow you to register")
        raise HTTPForbidden(msg)

    @property
    def buttons(self):
        return (deform.Button('register', title = _(u"Register"), css_class = 'btn btn-primary'),
                 self.button_cancel,)

    def register_success(self, appstruct):
        #FIXME: Protect against spamming?
        email = appstruct['email']
        factory = self.get_content_factory(u'Token')
        token = factory()
        rtokens = IRegistrationTokens(self.context)
        rtokens[email] = token
        html = self.render_template("arche:templates/emails/register.pt", token = token, email = email)
        send_email(_(u"Registration link"),
                   [email],
                   html,
                   request = self.request,
                   send_immediately = True)
        msg = _("reg_email_notification",
                default = "An email with registration instructions "
                "have been sent to the address you specified.")
        self.flash_messages.add(msg,
                                auto_destruct = False,
                                type="success")
        return HTTPFound(location = self.request.resource_url(self.root))


class RegisterFinishForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'register_finish'
    title = _(u"Complete registration")

    def __init__(self, context, request):
        super(RegisterFinishForm, self).__init__(context, request)
        if request.authenticated_userid != None:
            raise HTTPForbidden(_(u"Already logged in"))
        if not context.site_settings.get('allow_self_registration', False):
            raise HTTPForbidden(_(u"Site doesn't allow self registration"))
        rtokens = IRegistrationTokens(context)
        email = self.reg_email
        if not (email in rtokens and rtokens[email].valid and rtokens[email] == request.GET.get('t', object())):
            raise HTTPForbidden("Invalid")

    @property
    def reg_email(self):
        return self.request.GET.get('e', None)

    @property
    def buttons(self):
        return (deform.Button('register', title = _(u"Register"), css_class = 'btn btn-primary'),
                 self.button_cancel,)

    def register_success(self, appstruct):
        self.flash_messages.add(_(u"Welcome, you're now registered!"), type="success")
        factory = self.get_content_factory(u'User')
        userid = appstruct.pop('userid')
        email = self.reg_email
        obj = factory(email = email, **appstruct)
        self.context['users'][userid] = obj
        del IRegistrationTokens(self.context)[email]
        headers = remember(self.request, obj.userid)
        return HTTPFound(location = self.request.resource_url(obj), headers = headers)


class RecoverPasswordForm(BaseForm):
    type_name = u'Auth'
    schema_name = 'recover_password'
    title = _(u"Recover password")

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
        send_email(_(u"Password recovery request"),
                   [user.email],
                   html,
                   request = self.request)
        return self.relocate_response(self.request.resource_url(self.root))


def logout(context, request):
    headers = forget(request)
    request.session.delete()
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
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_view(RegisterFinishForm,
                    context = IRoot,
                    name = 'register_finish',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_view(RecoverPasswordForm,
                    context = IRoot,
                    name = 'recover_password',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_route('logout', '/logout')
    config.add_view(logout,
                    route_name = 'logout',
                    permission = security.NO_PERMISSION_REQUIRED)
