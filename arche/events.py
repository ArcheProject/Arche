from zope.interface import implementer
from repoze.folder.events import ObjectAddedEvent #API
from repoze.folder.events import ObjectWillBeRemovedEvent #API

from arche.interfaces import IEmailValidatedEvent
from arche.interfaces import IFormSuccessEvent
from arche.interfaces import IObjectUpdatedEvent
from arche.interfaces import ISchemaCreatedEvent
from arche.interfaces import IUser
from arche.interfaces import IViewInitializedEvent
from arche.interfaces import IWillLoginEvent
from arche.interfaces import IWorkflowAfterTransition
from arche.interfaces import IWorkflowBeforeTransition


@implementer(IObjectUpdatedEvent)
class ObjectUpdatedEvent(object):
    """ When an object has been updated in some way.
        Specifying changed or metadata as a list of strings might give a signal about
        catalog updates. None otherwise means that the catalog must update everything.
    """
    object = None
    changed = None
    metadata = None

    def __init__(self, _object, changed = None, metadata = None):
        self.object = _object
        if changed is not None:
            self.changed = frozenset(changed)
        if metadata is not None:
            self.metadata = frozenset(metadata)


@implementer(IViewInitializedEvent)
class ViewInitializedEvent(object):
    """ When a base content view has been initalized. It will not be used for views
        like thumbnail or download, where there's no reason to inject things at this point. """

    def __init__(self, _object):
        self.object = _object


@implementer(ISchemaCreatedEvent)
class SchemaCreatedEvent(object):
    """ Fire this event when schemas are instantiated.
    """
    def __init__(self, _object, view = None, request = None, context = None, **kw):
        self.object = _object
        self.view = view
        self.request = request
        self.context = context
        self.__dict__.update(**kw)


@implementer(IFormSuccessEvent)
class FormSuccessEvent(object):
    """ Raised when a form succeded validation. Ment as a plugin point for
        modifications before things are saved.
    """

    def __init__(self, _object, appstruct, form=None, **kw):
        self.object = _object
        self.request = _object.request
        self.context = _object.context
        self.appstruct = appstruct
        self.form = form  # The deform.Form instance
        self.__dict__.update(**kw)


@implementer(IEmailValidatedEvent)
class EmailValidatedEvent(object):
    __doc__ = IEmailValidatedEvent.__doc__

    def __init__(self, user, **kw):
        self.user = user
        if not user.email:
            raise ValueError("EmailValidatedEvent fired, but user had no email address")
        self.__dict__.update(**kw)


@implementer(IWillLoginEvent)
class WillLoginEvent(object):
    __doc__ = IWillLoginEvent.__doc__

    def __init__(self, user, request = None, first_login = False, auth_kw = {}, **kw):
        assert IUser.providedBy(user)
        self.user = user
        self.request = request
        self.first_login = first_login
        self.auth_kw = dict(auth_kw)
        self.__dict__.update(**kw)


class BaseWorkflowTransition(object):
    """ See intefaces.IWorkflowTransition. """

    def __init__(self, _object, workflow, transition, request = None):
        self.object = _object
        self.workflow = workflow
        self.transition = transition
        self.request = request
        self.to_state = transition.to_state
        self.from_state = transition.from_state


@implementer(IWorkflowBeforeTransition)
class WorkflowBeforeTransition(BaseWorkflowTransition):
    __doc__ = IWorkflowBeforeTransition.__doc__


@implementer(IWorkflowAfterTransition)
class WorkflowAfterTransition(BaseWorkflowTransition):
    __doc__ = IWorkflowAfterTransition.__doc__
