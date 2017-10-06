import re

import colander
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_root
from six import string_types

from arche import _
from arche import security
from arche.interfaces import IUser
from arche.interfaces import IUsers
from arche.utils import check_unique_name
from arche.utils import hash_method
from arche.utils import image_mime_to_title

NEW_USERID_PATTERN = re.compile(r'^[a-z]{1}[a-z0-9\-\_]{2,29}$')
RENAME_PATTERN = re.compile(r'^[a-zA-Z0-9\-\_\.]{1,50}$')


@colander.deferred
def unique_context_name_validator(node, kw):
    return UniqueContextNameValidator(kw['context'], kw['request'])


@colander.deferred
def unique_parent_context_name_validator(node, kw):
    return UniqueContextNameValidator(kw['context'].__parent__, kw['request'])


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
        if not RENAME_PATTERN.match(value):
            msg = _("Names can only contain charracters: A-Z, a-z, 0-9, '.', '-' or '_'")
            raise colander.Invalid(node, msg=msg)
        if not check_unique_name(self.context, self.request, value):
            raise colander.Invalid(node, msg=_("Already used within this context"))


class NewUserIDValidator(_BaseValidator):
    def __call__(self, node, value):
        assert IUsers.providedBy(self.context), "Can only be used on a Users object."
        if value != value.lower():
            msg = _("Please use lowercase only.")
            raise colander.Invalid(node, msg=msg)
        if not check_unique_name(self.context, self.request, value):
            msg = _("Already taken or conflicts with a restricted name.")
            raise colander.Invalid(node, msg=msg)
        if not NEW_USERID_PATTERN.match(value):
            msg = _('userid_char_error',
                    default="UserID must be 3-30 chars, start with lowercase a-z "
                            "and only contain lowercase a-z, numbers, minus and underscore.")
            raise colander.Invalid(node, msg=msg)


@colander.deferred
def allow_login_userid_or_email(node, kw):
    return AllowUserLoginValidator(kw['context'])


class AllowUserLoginValidator(object):
    def __init__(self, context):
        self.context = context

    def __call__(self, node, value):
        existing = ExistingUserIDOrEmail(self.context)
        existing(node, value)
        user = self.context['users'].get_user(value)
        if user.allow_login != True:
            raise colander.Invalid(node, _("Login disabled for this user"))


@colander.deferred
def login_password_validator(form, kw):
    context = kw['context']
    root = find_root(context)
    return LoginPasswordValidator(root)


def ascii_encodable_validator(node, value):
    try:
        str(value)
    except UnicodeEncodeError:
        raise colander.Invalid(node,
                               _("asci_encodable_error",
                                 default="Avoid non-english letters for this field."))


class LoginPasswordValidator(object):
    """ Validate a password during login. context must be site root."""

    def __init__(self, context):
        self.context = context

    def __call__(self, form, value):
        exc = colander.Invalid(form, u"Login invalid")  # Raised if trouble
        password = value['password']
        email_or_userid = value['email_or_userid']
        user = self.context['users'].get_user(email_or_userid)
        if not user:
            exc['email_or_userid'] = _("Invalid email or UserID")
            raise exc
        # Make sure one is set
        if not user.password:
            exc['password'] = _("no_password_set_error",
                                default=u"Password login disabled for this user. "
                                        "If you own the account you may request one to "
                                        "be set by using the recover password form.")
            raise exc
        # Validate password
        if not hash_method(password, hashed=user.password) == user.password:
            exc['password'] = _(u"Wrong password. Remember that passwords are case sensitive.")
            raise exc


@colander.deferred
def existing_userid_or_email(node, kw):
    return ExistingUserIDOrEmail(kw['context'])


@colander.deferred
def existing_userid_or_email_with_set_email(node, kw):
    return ExistingUserIDOrEmail(kw['context'], require_email=True)


class ExistingUserIDOrEmail(object):
    def __init__(self, context, require_email=False):
        self.context = find_root(context)
        self.require_email = require_email

    def __call__(self, node, value):
        if '@' in value:
            email_validator = colander.Email()
            email_validator(node, value)
        user = self.context['users'].get_user(value)
        if not user:
            raise colander.Invalid(node, _("Invalid email or UserID"))
        if self.require_email and not user.email:
            raise colander.Invalid(node, _("User doesn't have a valid email address"))


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
            # expect some kind of iterable with userids
            for userid in value:
                self._test(userid, node)

    def _test(self, userid, node):
        if userid not in self.context['users']:
            raise colander.Invalid(node, _("Can't find the UserID '${userid}'",
                                           mapping={'userid': userid}))


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
            # There's no usecase where this is okay
            if not IUser.providedBy(self.context):
                raise colander.Invalid(
                    node, _("already_registered_email_error",
                            default="Already registered. You may recover"
                                    "your password if you've lost it."))
            # Could be users own profile showing up
            if user.email != self.context.email:
                raise colander.Invalid(
                    node, _("already_used_email_error",
                            default="This address is already used."))


@colander.deferred
def supported_thumbnail_mimetype(node, kw):
    request = kw['request']
    msg = _("Not a valid image file! Any of these image types are supported: ${suggested}",
            mapping={'suggested': ", ".join(
                request.localizer.translate(x) for x in image_mime_to_title.values())})
    return FileUploadValidator(mimetypes=tuple(image_mime_to_title), msg=msg)


class FileUploadValidator(object):
    def __init__(self, mimetypes=(), msg=None):
        self.mimetypes = mimetypes
        self.msg = msg

    def __call__(self, node, value):
        mimetype = value.get('mimetype')
        if not mimetype:
            return  # We're okay with other kinds of data here!
        if mimetype not in self.mimetypes:
            msg = self.msg
            if msg is None:
                request = get_current_request()
                msg = _("Not a valid file type, try any of the following: ${suggested}",
                        mapping={'suggested': ", ".join(
                            request.localizer.translate(x) for x in self.mimetypes)})
            raise colander.Invalid(node, msg)


@colander.deferred
def deferred_current_password_validator(node, kw):
    context = kw['context']
    return CurrentPasswordValidator(context)


@colander.deferred
def deferred_current_pw_or_manager_validator(node, kw):
    context = kw['context']
    request = kw['request']
    if request.authenticated_userid != context.userid and request.has_permission(
            security.PERM_MANAGE_USERS, context):
        # Fetch managers pw instead
        root = find_root(context)
        admin_user = root['users'][request.authenticated_userid]
        return CurrentPasswordValidator(admin_user)
    return CurrentPasswordValidator(context)


class CurrentPasswordValidator(object):
    """ Check that current password matches. Used for sensitive operations
        when logged in to make sure that no one else changes the password for instance.
    """

    def __init__(self, context):
        assert IUser.providedBy(context)  # pragma : no cover
        self.context = context

    def __call__(self, node, value):
        if not hash_method(value, hashed=self.context.password) == self.context.password:
            raise colander.Invalid(
                node,
                _("Wrong password. Remember that passwords are case sensitive."))
