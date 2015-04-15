import re

from pyramid.traversal import find_root
import colander
from pyramid.threadlocal import get_current_request

from arche import _
from arche.interfaces import IUser
from arche.interfaces import IUsers
from arche.utils import check_unique_name
from arche.utils import hash_method
from arche.utils import image_mime_to_title
from six import string_types


NEW_USERID_PATTERN = re.compile(r'^[a-z]{1}[a-z0-9\-\_]{2,29}$')


@colander.deferred
def unique_context_name_validator(node, kw):
    return UniqueContextNameValidator(kw['context'], kw['request'])

@colander.deferred
def new_userid_validator(node, kw):
    root = find_root(kw['context'])
    request = kw['request']
    validator = request.registry.settings['arche.new_userid_validator']
    return validator(root['users'], request)


class _BaseValidator(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request


class UniqueContextNameValidator(_BaseValidator):
    def __call__(self, node, value):
        if not check_unique_name(self.context, self.request, value):
            raise colander.Invalid(node, msg = _(u"Already used within this context"))


class NewUserIDValidator(_BaseValidator):
    def __call__(self, node, value):
        assert IUsers.providedBy(self.context), "Can only be used on a Users object."
        if value != value.lower():
            msg = _("Please use lowercase only.")
            raise colander.Invalid(node, msg = msg)
        if not check_unique_name(self.context, self.request, value):
            msg = _("Already taken or conflicts with a restricted name.")
            raise colander.Invalid(node, msg = msg)
        if not NEW_USERID_PATTERN.match(value):
            msg = _('userid_char_error',
                    default = "UserID must be 3-30 chars, start with lowercase a-z and only contain lowercase a-z, numbers, minus and underscore.")
            raise colander.Invalid(node, msg = msg)


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
        if not hash_method(password, hashed = user.password) == user.password:
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
def existing_userids(node, kw):
    return ExistingUserIDs(kw['context'])

class ExistingUserIDs(object):

    def __init__(self, context):
        self.context = find_root(context)

    def __call__(self, node, value):
        if isinstance(value, string_types):
            self._test(value, node)
        else:
            #expect some kind of iterable with userids
            for userid in value:
                self._test(userid, node)

    def _test(self, userid, node):
        if userid not in self.context['users']:
            raise colander.Invalid(node, _("Can't find the UserID '${userid}'",
                                           mapping = {'userid': userid}))

@colander.deferred
def unique_email_validator(node, kw):
    return UniqueEmail(kw['context'])


class UniqueEmail(object):
    """ Make sure an email is unique. If it's used on an IUser object,
        it won't fail if the user tries to keep their own address.
    """
    def __init__(self, context):
        self.context = context

    def __call__(self, node, value):
        email_val = colander.Email()
        email_val(node, value)
        root = find_root(self.context)
        user = root['users'].get_user_by_email(value)
        if user:
            #There's no usecase where this is okay
            if not IUser.providedBy(self.context):
                raise colander.Invalid(node, _("already_registered_email_error",
                                               default = "Already registered. You may recover your password if you've lost it."))
            #Could be users own profile showing up
            if user.email != self.context.email:
                raise colander.Invalid(node, _("already_used_email_error",
                                               default = "This address is already used."))


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
    return FileUploadValidator(mimetypes = supported_mimes, msg = msg)


class FileUploadValidator(object):

    def __init__(self, mimetypes = (), msg = None):
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


@colander.deferred
def deferred_current_password_validator(node, kw):
    context = kw['context']
    return CurrentPasswordValidator(context)


class CurrentPasswordValidator(object):
    """ Check that current password matches. Used for sensitive operations
        when logged in to make sure that no one else changes the password for instance.
    """
    def __init__(self, context):
        assert IUser.providedBy(context) # pragma : no cover
        self.context = context

    def __call__(self, node, value):
        if not hash_method(value, hashed = self.context.password) == self.context.password:
            raise colander.Invalid(node, _("Wrong password. Remember that passwords are case sensitive."))
