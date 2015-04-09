from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.security import forget
from pyramid.security import remember
import deform

from arche import _
from arche import security
from arche.interfaces import IRegistrationTokens
from arche.interfaces import IRoot
from arche.views.base import BaseForm
from arche.views.base import DefaultEditForm


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
        return self.relocate_response(self.request.resource_url(self.root, 'recover_password'))
        
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
            self.flash_messages.add(msg, type = 'warning', require_commit = False)
            raise HTTPFound(location = request.resource_url(context))

    def get_schema(self):
        """ Fetch a combined schema if email validation should be skipped.
        """
        if self.root.skip_email_validation:
            return self.get_schema_factory(self.type_name, 'register_skip_validation')
        return self.get_schema_factory(self.type_name, self.schema_name)

    @property
    def buttons(self):
        return (deform.Button('register', title = _(u"Register"), css_class = 'btn btn-primary'),
                 self.button_cancel,)

    def register_success(self, appstruct):
        #FIXME: Protect against spamming?
        if self.root.skip_email_validation:
            return _finish_registration(self, appstruct)
        else:
            email = appstruct['email']
            factory = self.get_content_factory('Token')
            token = factory()
            rtokens = IRegistrationTokens(self.context)
            rtokens[email] = token
            url = self.request.resource_url(self.context, 'register_finish', query = {'t': token, 'e': email})
            html = self.render_template("arche:templates/emails/register.pt", token = token, email = email, url = url)
            self.request.send_email(_(u"Registration link"),
                                    [email],
                                    html,
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
            raise HTTPForbidden(_(u"Already logged in."))
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
        appstruct['email'] = self.reg_email
        return _finish_registration(self, appstruct)


def _finish_registration(view, appstruct):
    view.flash_messages.add(_("Welcome, you're now registered!"), type="success")
    factory = view.get_content_factory('User')
    userid = appstruct.pop('userid')
    if not view.root.skip_email_validation:
        appstruct['email_validated'] = True
    obj = factory(**appstruct)
    view.context['users'][userid] = obj
    try:
        del IRegistrationTokens(view.context)[appstruct['email']]
    except KeyError:
        #Validation is handled by the view already
        pass
    headers = remember(view.request, obj.userid)
    return HTTPFound(location = view.request.resource_url(view.root), headers = headers)


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
        url = self.request.resource_url(user, 'change_password', query = {'t': user.pw_token})
        html = self.render_template("arche:templates/emails/recover_password.pt", user = user, url = url)
        self.request.send_email(_(u"Password recovery request"),
                   [user.email],
                   html)
        return self.relocate_response(self.request.resource_url(self.root))


class UserChangePasswordForm(DefaultEditForm):
    type_name = 'User'
    schema_name = 'change_password'
    title = _("Change password")

    def __init__(self, context, request):
        #FIXME: Review this structure. Is it really smart to call super in two separate places?
        if request.authenticated_userid is None:
            token = getattr(context, 'pw_token', None)
            rtoken = request.GET.get('t', object())
            if token == rtoken and token.valid:
                #At this point the email address could be considered as validated too
                if context.email_validated == False:
                    context.email_validated = True
                super(UserChangePasswordForm, self).__init__(context, request)
                try:
                    del self.schema['current_password']
                except KeyError:
                    pass
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
        if self.request.authenticated_userid:
            self.flash_messages.add(_("Password changed"))
            return HTTPFound(location = self.request.resource_url(self.context))
        else:
            self.flash_messages.add(_("logged_in_changed_pw",
                                      default = "You've logged in and changed your password"))
            headers = remember(self.request, self.context.userid)
            return self.relocate_response(self.request.resource_url(self.context), headers = headers)


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
                    permission = security.PERM_REGISTER,
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
    config.add_view(UserChangePasswordForm,
                    context = 'arche.interfaces.IUser',
                    name = 'change_password',
                    permission = security.NO_PERMISSION_REQUIRED,
                    renderer = 'arche:templates/form.pt')
    config.add_route('logout', '/logout')
    config.add_view(logout,
                    route_name = 'logout',
                    permission = security.NO_PERMISSION_REQUIRED)
