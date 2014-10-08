from __future__ import unicode_literals
from UserDict import IterableUserDict
from logging import getLogger

from pyramid.httpexceptions import HTTPForbidden
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from zope.component import adapter
from zope.component.event import objectEventNotify
from zope.interface.declarations import implementer

from arche import _
from arche import security
from arche.events import WorkflowAfterTransition
from arche.events import WorkflowBeforeTransition
from arche.interfaces import IContextACL
from arche.interfaces import IWorkflow


class WorkflowException(Exception):
    pass


@implementer(IWorkflow)
@adapter(IContextACL)
class Workflow(object):
    """ Base adapter for workflows. All workflows should inherit this one.
    """
    name = ''
    title = ''
    description = ''
    states = {}
    transitions = {}
    initial_state = ''

    def __init__(self, context):
        self.context = context

    @property
    def state(self): return getattr(self.context, '__wf_state__', self.initial_state)
    @state.setter
    def state(self, value):
        assert value in self.states, "No state named '%s'" % value
        self.context.__wf_state__ = value

    @property
    def state_title(self):
        return self.states.get(self.state, _("<Not found>"))

    @classmethod
    def init_acl(cls, registry):
        pass

    def get_transitions(self, request = None):
        if request is None:
            request = get_current_request()
        for trans in self.transitions.values():
            if trans.from_state == self.state and request.has_permission(trans.permission, self.context):
                yield trans

    def do_transition(self, name, request = None):
        #Check permission, treat input as unsafe!
        if request is None:
            request = get_current_request()
        trans = self.transitions[name]
        if trans.from_state != self.state:
            raise ValueError("The transition '%s' cant go from state '%s'" % (trans.name, self.state))
        if not request.has_permission(trans.permission, self.context):
            raise HTTPForbidden("Wrong permissions for this transition")
        objectEventNotify(WorkflowBeforeTransition(self.context, self, trans))
        self.state = trans.to_state
        objectEventNotify(WorkflowAfterTransition(self.context, self, trans))
        return trans


class Transition(object):
    """ Simple transition objects to keep track of transitions and what they do.
    """
    from_state = ''
    to_state = ''
    permission = ''
    title = ''
    message = ''

    def __init__(self, from_state = '', to_state = '',
                 permission = '', title = '', message = ''):
        self.from_state = from_state
        self.to_state = to_state
        self.permission = permission
        self.title = title
        self.message = message

    @property
    def name(self):
        return "%s:%s" % (self.from_state, self.to_state)


_simple_public_to_private = \
    Transition(from_state = 'public',
               to_state = 'private',
               permission = security.PERM_EDIT,
               title = _("Make private"),
               message = _("Now private"))
_simple_private_to_public = \
    Transition(from_state = 'private',
               to_state = 'public',
               permission = security.PERM_EDIT,
               title = _("Publish"),
               message = _("Published"))


class SimpleWorkflow(Workflow):
    """ Private public workflow."""
    name = 'simple_workflow'
    title = _("Simple")
    states = {'private': _("Private"),
              'public': _("Public")}
    transitions = {_simple_public_to_private.name: _simple_public_to_private,
                   _simple_private_to_public.name: _simple_private_to_public}
    initial_state = 'private'

    @classmethod
    def init_acl(cls, registry):
        acl_reg = security.get_acl_registry(registry)
        priv_name = "%s:private" % cls.name
        acl_reg[priv_name] = security.ACLEntry()
        acl_reg[priv_name].add(security.ROLE_ADMIN, security.ALL_PERMISSIONS)
        acl_reg[priv_name].add(security.ROLE_OWNER, [security.PERM_VIEW, security.PERM_EDIT, security.PERM_DELETE])
        acl_reg[priv_name].add(security.ROLE_EDITOR, [security.PERM_VIEW, security.PERM_EDIT, security.PERM_DELETE])
        acl_reg[priv_name].add(security.ROLE_VIEWER, [security.PERM_VIEW])


_rev_public_to_private = Transition(from_state = 'public',
                                    to_state = 'private',
                                    permission = security.PERM_EDIT,
                                    title = _("Make private"),
                                    message = _("Now private"))
_rev_private_to_public = Transition(from_state = 'private',
                                    to_state = 'public',
                                    permission = security.PERM_REVIEW_CONTENT,
                                    title = _("Publish"),
                                    message = _("Published"))
_rev_private_to_review = Transition(from_state = 'private',
                                    to_state = 'review',
                                    permission = security.PERM_EDIT,
                                    title = _("Submit for review"),
                                    message = _("Submitted for review"))
_rev_review_to_private = Transition(from_state = 'review',
                                    to_state = 'private',
                                    permission = security.PERM_EDIT,
                                    title = _("Make private"),
                                    message = _("Now private"))
_rev_public_to_review = Transition(from_state = 'public',
                                    to_state = 'review',
                                    permission = security.PERM_REVIEW_CONTENT,
                                    title = _("Retract and resubmit for review"),
                                    message = _("Retracted and resubmitted for review"))
_rev_review_to_public = Transition(from_state = 'review',
                                    to_state = 'public',
                                    permission = security.PERM_REVIEW_CONTENT,
                                    title = _("Publish"),
                                    message = _("Published"))


class ReviewWorkflow(Workflow):
    """ Content must be reviewed before published."""
    name = 'review_workflow'
    title = _("Review workflow")
    states = {'private': _("Private"),
              'public': _("Public"),
              'review': _("Review")}
    transitions = {_rev_public_to_private.name: _rev_public_to_private,
                   _rev_private_to_public.name: _rev_private_to_public,
                   _rev_private_to_review.name: _rev_private_to_review,
                   _rev_review_to_private.name: _rev_review_to_private,
                   _rev_public_to_review.name: _rev_public_to_review,
                   _rev_review_to_public.name: _rev_review_to_public,}
    initial_state = 'private'

    @classmethod
    def init_acl(cls, registry):
        acl_reg = security.get_acl_registry(registry)
        priv_name = "%s:private" % cls.name
        acl_reg[priv_name] = security.ACLEntry()
        acl_reg[priv_name].add(security.ROLE_ADMIN, security.ALL_PERMISSIONS)
        acl_reg[priv_name].add(security.ROLE_OWNER, [security.PERM_VIEW, security.PERM_EDIT, security.PERM_DELETE])
        acl_reg[priv_name].add(security.ROLE_EDITOR, [security.PERM_VIEW, security.PERM_EDIT, security.PERM_DELETE])
        acl_reg[priv_name].add(security.ROLE_VIEWER, [security.PERM_VIEW])
        acl_reg[priv_name].add(security.ROLE_REVIEWER, [security.PERM_REVIEW_CONTENT]) #May not be able to view
        rev_name = "%s:review" % cls.name
        acl_reg[rev_name] = security.ACLEntry()
        acl_reg[rev_name].add(security.ROLE_ADMIN, security.ALL_PERMISSIONS)
        acl_reg[rev_name].add(security.ROLE_OWNER, [security.PERM_VIEW])
        acl_reg[rev_name].add(security.ROLE_EDITOR, [security.PERM_VIEW])
        acl_reg[rev_name].add(security.ROLE_VIEWER, [security.PERM_VIEW])
        acl_reg[rev_name].add(security.ROLE_REVIEWER, [security.PERM_VIEW, security.PERM_REVIEW_CONTENT])
        pub_name = "%s:public" % cls.name
        acl_reg[pub_name] = security.ACLEntry()
        acl_reg[pub_name].add(security.ROLE_ADMIN, security.ALL_PERMISSIONS)
        acl_reg[pub_name].add(security.Everyone, [security.PERM_VIEW])
        acl_reg[pub_name].add(security.ROLE_REVIEWER, [security.PERM_REVIEW_CONTENT])


class WorkflowRegistry(IterableUserDict):
    """ Registry for workflow information, and set workflow for different content types. """

    def __init__(self):
        self.data = {}
        self.content_type_mapping = {}

    def set_wf(self, type_name, wf_name):
        """ Set workflow for a specific content type. """
        self.content_type_mapping[type_name] = wf_name

    def get_wf(self, type_name):
        """ Return mapped workflow name for a content type. """
        return self.content_type_mapping.get(type_name, None)


def get_context_wf(context, registry = None):
    """ Get workflow for a specific context. It must implement the
        arche.interfaces.IContextACL to be able to work, and a workflow must be set.
    """
    if registry is None:
        registry = get_current_registry()
    wfs = get_workflows(registry)
    wf_name = wfs.get_wf(getattr(context, 'type_name', None))
    return registry.queryAdapter(context, IWorkflow, name = wf_name)

def get_workflows(registry = None):
    """ Returns the workflow registry. """
    if registry is None:
        registry = get_current_registry()
    try:
        return registry._workflows
    except AttributeError:
        raise WorkflowException("Workflows not configured")

def add_workflow(config, workflow):
    """ Add a workflow object so it will be usable by Arche or subcomponents.
    """
    assert IWorkflow.implementedBy(workflow), "Workflows must always implement IWorkflow"
    config.registry.registerAdapter(workflow, name = workflow.name)
    wfs = config.registry._workflows
    wfs[workflow.name] = workflow
    workflow.init_acl(config.registry)

def set_content_workflow(config, type_name, wf_name):
    """ Set workflow for a specific content type. """
    wfs = get_workflows(config.registry)
    wfs.set_wf(type_name, wf_name)

def read_paster_wf_config(config):
    """ Read workflow configuration from paster settings.
        Expects input like:
        
        arche.workflows =
            Document simple_workflow
            Image other_workflow
    """
    settings = config.registry.settings
    wf_conf = settings.get('arche.workflows', '')
    for row in wf_conf.splitlines():
        if not row:
            continue
        try:
            type_name, wf_name = row.split()
        except ValueError:
            logger = getLogger(__name__)
            msg = "Workflow configuration error - can't understand this line: '%s'" % row
            logger.warn(msg)
        config.set_content_workflow(type_name, wf_name)

def includeme(config):
    config.registry._workflows = WorkflowRegistry()
    config.add_directive('add_workflow', add_workflow)
    config.add_workflow(SimpleWorkflow)
    config.add_workflow(ReviewWorkflow)
    config.add_directive('set_content_workflow', set_content_workflow)
    read_paster_wf_config(config)
