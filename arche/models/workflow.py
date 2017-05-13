from __future__ import unicode_literals

from pyramid.httpexceptions import HTTPForbidden
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.traversal import find_resource
from pyramid.traversal import find_root
from pyramid.traversal import resource_path
from zope.component import adapter
from zope.component.event import objectEventNotify
from zope.interface.declarations import implementer
import six

from arche import _
from arche import logger
from arche import security
from arche.compat import IterableUserDict
from arche.events import WorkflowAfterTransition
from arche.events import WorkflowBeforeTransition
from arche.interfaces import IContextACL
from arche.interfaces import IWorkflow
from arche.exceptions import WorkflowException
from arche.events import ObjectUpdatedEvent


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
        pass #pragma : no coverage

    @classmethod
    def add_transitions(cls, from_states = '', to_states = '',
                       permission = "__NOT_ALLOWED__", title = None,
                       message = '', create_states = False):
        """
        :param from_states: '*' for all current states, or state name, or an iterator with state names.
        :param to_states: '*' for all current states, or state name, or an iterator with state names.
        :param permission: The required permission or None
        :param title: Name of the transition, like "Publish"
        :param message: Message to display when it was executed, like "Item was published"
        :return: created transition(s)

        A quick shortcut to create transitions.
        """
        from_states = cls._get_states(from_states, create = create_states)
        to_states = cls._get_states(to_states, create = create_states)
        results = []
        for fstate in from_states:
            for tstate in to_states:
                if tstate == fstate:
                    continue
                transition = Transition(from_state = fstate,
                                        to_state = tstate,
                                        permission=permission,
                                        title=title != None and title or cls.states[tstate],
                                        message=message)
                if transition.name in cls.transitions:
                    logger.warn("Overriding tranistion %r in workflow %r", transition.name, cls.name)
                cls.transitions[transition.name] = transition
                results.append(transition)
        return results

    @classmethod
    def _get_states(cls, states, create = False):
        found_states = set()
        if states == '*':
            found_states.update(cls.states)
        elif isinstance(states, six.string_types):
            found_states.add(states)
        else:
            found_states.update(states)
        for state in found_states:
            if state not in cls.states:
                if create:
                    cls.states[state] = state
                else:
                    raise KeyError("No state called %r for %r" % (state, cls))
        if not found_states:
            raise ValueError("No states to work with")
        return found_states

    def get_transitions(self, request = None):
        if request is None:
            request = get_current_request()
        for trans in self.transitions.values():
            if trans.from_state == self.state and request.has_permission(trans.permission, self.context):
                yield trans

    def do_transition(self, name, request = None, force = False):
        """
        :param name: Either the name of the transision or the expected state
        :param request: current request
        :param force: Do transition regardless of permission.
        :return: transition
        """
        #Check permission, treat input as unsafe!
        if request is None:
            request = get_current_request()
        if ':' not in name:
            name = "%s:%s" % (self.state, name)
        try:
            trans = self.transitions[name]
        except KeyError:
            raise WorkflowException("The workflow '%s' doesn't have any transition with the id '%s'." % (self.name, name))
        if trans.from_state != self.state and force is False:
            raise ValueError("The transition '%s' cant go from state '%s'" % (trans.name, self.state))
        if not request.has_permission(trans.permission, self.context) and force is False:
            if request.registry.settings.get('arche.debug', False):
                raise Exception("Wrong permissions for this transition")
            raise HTTPForbidden("Wrong permissions for this transition")
        objectEventNotify(WorkflowBeforeTransition(self.context, self, trans, request = request))
        self.state = trans.to_state
        #Any object implementing IContextACL will have the attribute wf_state that stores workflow state name
        objectEventNotify(ObjectUpdatedEvent(self.context, changed = ('wf_state',)))
        objectEventNotify(WorkflowAfterTransition(self.context, self, trans, request = request))
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
        self.title = title and title or to_state
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
        acl_reg[priv_name] = 'private'
        pub_name = "%s:public" % cls.name
        acl_reg[pub_name] = 'public'


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
        acl_reg[priv_name] = 'private'
        rev_name = "%s:review" % cls.name
        acl_reg[rev_name] = 'review'
        pub_name = "%s:public" % cls.name
        acl_reg[pub_name] = 'public'


class InheritWorkflow(Workflow):
    """ Always inherit workflow from it's parent. Make sure there is a parent somewhere to inherit from!"""
    name = 'inherit'
    title = _("Inherit workflow")
    states = {'inherit': _("Inherit")}
    transitions = {}
    initial_state = 'inherit'

    @classmethod
    def init_acl(cls, registry):
        acl_reg = security.get_acl_registry(registry)
        acl_reg['%s:inherit' % cls.name] = 'inherit'


class WorkflowRegistry(IterableUserDict):
    """ Registry for workflow information, and set workflow for different content types. """

    def __init__(self):
        self.data = {}
        self.content_type_mapping = {}

    def set_wf(self, type_name, wf_name):
        """ Set workflow for a specific content type.
            Unset by assigning None."""
        if wf_name is None:
            logger.debug("Removing workflow for %r" % type_name)
            self.content_type_mapping.pop(type_name, None)
        else:
            assert isinstance(wf_name, six.string_types), "wf_name must be a string, got: %r" % wf_name
            logger.debug("Workflow for %r set to %r" % (type_name, wf_name))
            self.content_type_mapping[type_name] = wf_name
            if self.get_wf_adapter(wf_name) is None:
                logger.warning("%r got a workflow assigned with the name %r, "
                               "but there's no workflow registered with "
                               "that name.", type_name, wf_name)

    def get_wf(self, type_name):
        """ Return mapped workflow name for a content type. """
        return self.content_type_mapping.get(type_name, None)

    def get_wf_adapter(self, wf_name, default = None):
        registry = get_current_registry()
        for ar in registry.registeredAdapters():
            if ar.name == wf_name and ar.provided == IWorkflow:
                return ar.factory
        return default


def get_context_wf(context, registry = None):
    """ Get workflow for a specific context. It must implement the
        arche.interfaces.IContextACL to be able to work, and a workflow must be set.
        However, it won't fail if no workflow is configured or set.
    """
    if registry is None:
        registry = get_current_registry()
    wfs = get_workflows(registry)
    if wfs != None:
        wf_name = wfs.get_wf(getattr(context, 'type_name', None))
        if wf_name:
            return registry.queryAdapter(context, IWorkflow, name = wf_name)


def get_workflows(registry = None):
    """ Returns the workflow registry. """
    if registry is None: #pragma : no coverage
        registry = get_current_registry()
    try:
        return registry.workflows
    except AttributeError: #This could be by choice
        logger.debug("Workflows not configured")

def add_workflow(config, workflow):
    """ Add a workflow object so it will be usable by Arche or subcomponents.
    """
    assert IWorkflow.implementedBy(workflow), "Workflows must always implement IWorkflow"
    config.registry.registerAdapter(workflow, name = workflow.name)
    wfs = config.registry.workflows
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
        items = row.split()
        if len(items) == 1:
            config.set_content_workflow(items[0], None)
        elif len(items) == 2:
            config.set_content_workflow(items[0], items[1])
        else: #pragma : no coverage
            logger.warn("This row in the workflow configuration wasn't understood: %r" % row)

def bulk_state_change(context, from_state, to_state, request = None, type_name = None, perm = None, force = True):
    """ Change all items from a state to another. This script will use the catalog to find items.

        context
            Include this context and everything below.
            Use root for everything.


        from_state
            Id of current state required.

        to_state
            Id to end up in.

        type_name
            What kind of type to change

        perm
            Require this perm on result, or None to apply on all.

        force
            Force transition regardless of permissions.
    """
    if request is None:
        request = get_current_request()
    root = find_root(context)
    query = "path == '%s' and " % resource_path(context)
    query += "wf_state == '%s'" % from_state
    if type_name:
        query += " and type_name == '%s'" % type_name
    for docid in root.catalog.query(query)[1]:
        path = root.document_map.address_for_docid(docid)
        obj = find_resource(root, path)
        wf = get_context_wf(obj, request.registry)
        if wf:
            wf.do_transition("%s:%s" % (from_state, to_state), force = force)

def includeme(config):
    if hasattr(config.registry, 'workflows'):
        logger.warn("arche.models.workflow has already been loaded. Aborting")
        return
    config.registry.workflows = WorkflowRegistry()
    config.add_directive('add_workflow', add_workflow)
    config.add_workflow(SimpleWorkflow)
    config.add_workflow(ReviewWorkflow)
    config.add_workflow(InheritWorkflow)
    config.add_directive('set_content_workflow', set_content_workflow)
