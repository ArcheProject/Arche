from pyramid.traversal import find_root
import colander

from arche import _
from arche.interfaces import IUsers
from arche.utils import check_unique_name
from arche.utils import generate_slug
from arche.utils import hash_method
from arche.utils import image_mime_to_title
from pyramid.threadlocal import get_current_request

@colander.deferred
def unique_context_name_validator(node, kw):
    return UniqueContextNameValidator(kw['context'], kw['request'])


@colander.deferred
def unique_userid_validator(node, kw):
    root = find_root(kw['context'])
    request = kw['request']
    return UniqueUserIDValidator(root['users'], request)


class _BaseValidator(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


class UniqueContextNameValidator(_BaseValidator):
    def __call__(self, node, value):
        if not check_unique_name(self.context, self.request, value):
            raise colander.Invalid(node, msg = _(u"Already used within this context"))


class UniqueUserIDValidator(_BaseValidator):
    def __call__(self, node, value):
        assert IUsers.providedBy(self.context), "Can only be used on a Users object."
        if value in self.context:
            msg = _("Already taken")
            raise colander.Invalid(node, msg = msg)
        if generate_slug(self.context, value) != value:
            raise colander.Invalid(node, msg = _("Use lowercase with only a-z or numbers."))


@colander.deferred
def login_password_validator(form, kw):
    context = kw['context']
    root = find_root(context)
    return LoginPasswordValidator(root)


class LoginPasswordValidator(object):
    """ Validate a password during login. context must be site root."""
    
    def __init__(self, context):
        self.context = context
        
    def __call__(self, form, value):
        exc = colander.Invalid(form, u"Login invalid") #Raised if trouble
        password = value['password']
        email_or_userid = value['email_or_userid']
        if '@' in email_or_userid:
            user = self.context['users'].get_user_by_email(email_or_userid)
        else:
            user = self.context['users'].get(email_or_userid, None)
        if not user:
            exc['email_or_userid'] = _("Invalid email or UserID")
            raise exc
        #Validate password
        if not hash_method(password) == user.password:
            exc['password'] = _(u"Wrong password. Remember that passwords are case sensitive.")
            raise exc


@colander.deferred
def existing_userid_or_email(node, kw):
    return ExistingUserIDOrEmail(kw['context'])


class ExistingUserIDOrEmail(object):

    def __init__(self, context):
        self.context = find_root(context)

    def __call__(self, node, value):
        if '@' in value:
            user = self.context['users'].get_user_by_email(value)
        else:
            user = self.context['users'].get(value, None)
        if not user:
            raise colander.Invalid(node, _("Invalid email or UserID"))


@colander.deferred
def unique_email_validator(node, kw):
    return UniqueEmail(kw['context'])


class UniqueEmail(object):
    def __init__(self, context):
        self.context = find_root(context)

    def __call__(self, node, value):
        email_val = colander.Email()
        email_val(node, value)
        if self.context['users'].get_user_by_email(value) is not None:
            raise colander.Invalid(node, _("Already registered. You may recover your password if you've lost it."))


@colander.deferred
def supported_thumbnail_mimetype(node, kw):
    request = kw['request']
    supported_mimes = request.registry.settings['supported_thumbnail_mimetypes']
    suggested = set()
    for (k, v) in image_mime_to_title.items():
        if k in supported_mimes:
            suggested.add(v)
    msg = _("Not a valid image file! Any of these image types are supported: ${suggested}",
            mapping = {'suggested': ", ".join(request.localizer.translate(x) for x in suggested)})
    return MimeTypeValidator(supported_mimes, msg = msg)


class MimeTypeValidator(object):

    def __init__(self, mimetypes, msg = None):
        self.mimetypes = mimetypes
        self.msg = msg

    def __call__(self, node, value):
        mimetype = value.get('mimetype')
        if not mimetype:
            return #We're okay with other kinds of data here!
        if mimetype not in self.mimetypes:
            msg = self.msg
            if msg is None:
                request = get_current_request()
                msg = _("Not a valid file type, try any of the following: ${suggested}",
                        mapping = {'suggested': ", ".join(request.localizer.translate(x) for x in self.mimetypes)})
            raise colander.Invalid(node, msg)
