import colander
from pyramid.traversal import find_root

from arche.utils import check_unique_name
from arche.utils import hash_method
from arche import _


@colander.deferred
def unique_context_name_validator(node, kw):
    return UniqueContextNameValidator(kw['context'], kw['request'])


@colander.deferred
def unique_userid_validator(node, kw):
    root = find_root(kw['context'])
    request = kw['request']
    return UniqueContextNameValidator(root['users'], request)


class UniqueContextNameValidator(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, node, value):
        if not check_unique_name(self.context, self.request, value):
            raise colander.Invalid(node, msg = _(u"Already used within this context"))


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
        user = self.context['users'].get_user_by_email(value['email'])
        if not user:
            exc['email'] = _("Invalid email")
            raise exc
        #Validate password
        if not hash_method(password) == user.password:
            exc['password'] = _(u"Wrong password. Remember that passwords are case sensitive.")
            raise exc
