from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPForbidden

from arche import _
from arche import security
from arche.interfaces import IEmailValidationTokens
from arche.views.base import BaseView
from arche.views.base import DefaultAddForm
from arche.views.base import DefaultEditForm
from arche.utils import fail_marker


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
        email_changed = appstruct['email'] != self.context.email
        if email_changed and not self.root.skip_email_validation:
            email = appstruct.pop('email')
            val_tokens = IEmailValidationTokens(self.context)
            token = val_tokens.new(email)
            url = self.request.resource_url(self.context, 'change_email', query = {'t': token, 'e': email})
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

    def __call__(self):
        
        rtoken = self.request.GET.get('t', fail_marker)
        email = self.request.GET.get('e', fail_marker)
        val_tokens = IEmailValidationTokens(self.context)
        try:
            token = val_tokens[email]
        except KeyError:
            raise HTTPForbidden(_("No such token"))
        if not token.valid:
            raise HTTPForbidden(_("The email change request has expired."))
        if token == rtoken:
            #FIXME: Email old address?
            del val_tokens[email]
            self.context.update(email = email, email_validated = True) #So events fire
            self.flash_messages.add(_("Email changed"))
            return HTTPFound(location = self.request.resource_url(self.context))
        raise HTTPForbidden(_("This link is invalid. Unable to change email."))


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
                    name = 'change_email',
                    permission = security.PERM_EDIT)
