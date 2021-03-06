from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden

from arche import _
from arche import security
from arche.interfaces import IEmailValidationTokens
from arche.utils import fail_marker
from arche.views.base import BaseView
from arche.views.base import DefaultAddForm
from arche.views.base import DefaultEditForm
from arche.views.base import DynamicView


class AddUserForm(DefaultAddForm):
    type_name = 'User'

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        userid = appstruct.pop('userid')
        obj = factory(**appstruct)
        self.context[userid] = obj
        return HTTPFound(location = self.request.resource_url(obj))


class EditUserForm(DefaultEditForm):

    def save_success(self, appstruct):
        admin_override_skip_validation = appstruct.pop('admin_override_skip_validation', False)
        email_changed = appstruct['email'] != self.context.email
        if email_changed and not (self.root.skip_email_validation or admin_override_skip_validation or not appstruct['email']):
            email = appstruct.pop('email')
            val_tokens = IEmailValidationTokens(self.context)
            token = val_tokens.new(email)
            url = self.request.resource_url(self.context, '_ve', query = {'t': token, 'e': email})
            html = self.render_template("arche:templates/emails/email_change.pt", user = self.context, url = url)
            self.request.send_email(_(u"Email change validation"),
                                    [email],
                                    html)
            msg = _("require_email_verification_notice",
                    default = "Since you requested to change your email address "
                    "we've sent you an email to verify your new address. "
                    "As soon as you click the link in your email, "
                    "your address will change. All other changes were saved.")
            self.flash_messages.add(msg, type="warning", auto_destruct = False)
        else:
            if email_changed:
                self.context.email_validated = False
            self.flash_messages.add(self.default_success, type="success")
        self.context.update(**appstruct)
        return HTTPFound(location = self.request.resource_url(self.context))


class ChangeEmailView(BaseView):
    """ Change or validate an address. """

    def __call__(self):
        rtoken = self.request.GET.get('t', fail_marker)
        email = self.request.GET.get('e', fail_marker)
        val_tokens = IEmailValidationTokens(self.context)
        try:
            token = val_tokens[email]
        except KeyError:
            raise HTTPForbidden(_("No such token"))
        if not token.valid:
            raise HTTPForbidden(_("Expired."))
        if token == rtoken:
            #FIXME: Email old address?
            del val_tokens[email]
            if self.context.email != email:
                self.context.update(email = email, email_validated = True) #So events fire
                self.flash_messages.add(_("Email changed"))
            else:
                self.context.update(email_validated = True)
                self.flash_messages.add(_("Email validated"))
            return HTTPFound(location = self.request.resource_url(self.context))
        raise HTTPForbidden(_("This link is invalid."))


class RequestEmailValidationView(BaseView):

    def __call__(self):
        if not self.context.email:
            raise HTTPBadRequest(_("No email set"))
        if not self.context.email_validated:
            val_tokens = IEmailValidationTokens(self.context)
            token = val_tokens.new(self.context.email)
            url = self.request.resource_url(self.context, '_ve', query = {'t': token, 'e': self.context.email})
            html = self.render_template("arche:templates/emails/email_validate.pt", user = self.context, url = url)
            self.request.send_email(_("Email validation"),
                                    [self.context.email],
                                    html)
            self.flash_messages.add(_("We sent you an email with a link to confirm your address."))
        else:
            self.flash_messages.add(_("Your address is already validated."))
        came_from = self.request.GET.get('came_from', None)
        if came_from:
            url = came_from
        else:
            url = self.request.resource_url(self.context)
        return HTTPFound(location=url)


class UserView(DynamicView):
    pass


def includeme(config):
    config.add_view(AddUserForm,
                    context = 'arche.interfaces.IUsers',
                    name = 'add',
                    request_param = "content_type=User",
                    permission = security.PERM_MANAGE_USERS, #FIXME: Not add user perm?
                    renderer = 'arche:templates/form.pt')
    config.add_view(EditUserForm,
                    context = 'arche.interfaces.IUser',
                    name = 'edit',
                    permission = security.PERM_EDIT,
                    renderer = 'arche:templates/form.pt')
    config.add_view(ChangeEmailView,
                    context = 'arche.interfaces.IUser',
                    name = '_ve',
                    permission = security.PERM_EDIT)
    config.add_view(RequestEmailValidationView,
                    context = 'arche.interfaces.IUser',
                    name = 'validate_email',
                    permission = security.PERM_EDIT)
    config.add_view(UserView,
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/content/user.pt",
                    context = 'arche.interfaces.IUser')
