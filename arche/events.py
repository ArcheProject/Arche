from zope.interface import implementer
from repoze.folder.events import (ObjectAddedEvent,
                                  ObjectWillBeRemovedEvent) #API

from arche.interfaces import (IObjectUpdatedEvent,
                              IViewInitializedEvent,
                              ISchemaCreatedEvent,
                              IWorkflowBeforeTransition,
                              IWorkflowAfterTransition)


@implementer(IObjectUpdatedEvent)
class ObjectUpdatedEvent(object):
    """ When an object has been updated in some way.
    """
    object = None
    changed = frozenset()
    
    def __init__(self, _object, changed = ()):
        self.object = _object
        self.changed = set(changed)


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
    
    def __init__(self, _object):
        self.object = _object


class _WorkflowTransition(object):

    def __init__(self, _object, workflow, transition):
        self.object = _object
        self.workflow = workflow
        self.transition = transition


@implementer(IWorkflowBeforeTransition)
class WorkflowBeforeTransition(_WorkflowTransition):
    pass


@implementer(IWorkflowAfterTransition)
class WorkflowAfterTransition(_WorkflowTransition):
    pass
