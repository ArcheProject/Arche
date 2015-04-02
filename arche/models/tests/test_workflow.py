from unittest import TestCase

from pyramid import testing
from zope.interface.verify import verifyClass, verifyObject
from pyramid.httpexceptions import HTTPForbidden

from arche.interfaces import IWorkflow, IWorkflowBeforeTransition, IWorkflowAfterTransition, IContextACL


def _mk_dummy():
    from arche.resources import ContextACLMixin
    class _Dummy(testing.DummyResource, ContextACLMixin):
        type_name = 'Dummy'
    return _Dummy()

def _mk_dummy_transition(**kw):
    from arche.models.workflow import Transition
    kwargs = dict(from_state = 'current',
                  to_state = 'future',
                  permission = 'dummy perm',
                  title = "Hello transition",
                  message = "Something going on")
    kwargs.update(kw)
    return Transition(**kwargs)


class WorkflowTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())
 
    def tearDown(self):
        testing.tearDown()

    @property
    def _cut(self):
        from arche.models.workflow import Workflow
        return Workflow

    def test_verify_class(self):
        verifyClass(IWorkflow, self._cut)

    def test_verify_object(self):
        verifyObject(IWorkflow, self._cut(_mk_dummy()))

    def test_state_title(self):
        obj = self._cut(_mk_dummy())
        obj.states['one'] = 'Hello'
        obj.initial_state = 'one'
        self.assertEqual(obj.state_title, 'Hello')

    def test_get_transitions(self):
        obj = self._cut(_mk_dummy())
        obj.initial_state = 'current'
        one = _mk_dummy_transition()
        two = _mk_dummy_transition(from_state = 'other')
        obj.transitions['one'] = one
        obj.transitions['two'] = two
        self.assertEqual(tuple(obj.get_transitions()), (one,))

    def test_get_transitions_wrong_perm(self):
        self.config.testing_securitypolicy('userid', permissive = False)
        obj = self._cut(_mk_dummy())
        obj.initial_state = 'current'
        one = _mk_dummy_transition()
        two = _mk_dummy_transition(from_state = 'other')
        obj.transitions['one'] = one
        obj.transitions['two'] = two
        self.assertEqual(tuple(obj.get_transitions()), ())

    def test_do_transition(self):
        obj = self._cut(_mk_dummy())
        obj.initial_state = 'current'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one'] = one
        obj.do_transition('one')
        self.assertEqual(obj.state, 'future')

    def test_do_transition_wrong_transition(self):
        obj = self._cut(_mk_dummy())
        obj.initial_state = 'other'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one'] = one
        self.assertRaises(ValueError, obj.do_transition, 'one')

    def test_do_transition_force_wrong_initial_state(self):
        obj = self._cut(_mk_dummy())
        obj.initial_state = 'other'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one'] = one
        obj.do_transition('one', force = True)
        self.assertEqual(obj.state, 'future')

    def test_do_transition_force_wrong_perm(self):
        self.config.testing_securitypolicy('userid', permissive = False)
        obj = self._cut(_mk_dummy())
        obj.initial_state = 'current'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one'] = one
        obj.do_transition('one', force = True)
        self.assertEqual(obj.state, 'future')

    def test_do_transition_wrong_perm(self):
        self.config.testing_securitypolicy('userid', permissive = False)
        obj = self._cut(_mk_dummy())
        obj.initial_state = 'current'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one'] = one
        self.assertRaises(HTTPForbidden, obj.do_transition, 'one')


class WorkflowIntegrationTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())
        self.config.include('arche.utils')
        self.config.include('arche.security')
        self.config.include('arche.models.workflow')
 
    def tearDown(self):
        testing.tearDown()

    def test_set_and_get_wf(self):
        wfs = self.config.registry.workflows
        self.assertEqual(wfs.get_wf('Document'), None)
        wfs.set_wf('Document', 'simple_workflow')
        self.assertEqual(wfs.get_wf('Document'), 'simple_workflow')

    def test_get_context_wf(self):
        from arche.models.workflow import get_context_wf
        dummy = _mk_dummy()
        #self.assertEqual(get_context_wf(dummy), None)
        self.config.set_content_workflow('Dummy', 'simple_workflow')
        wf_obj = get_context_wf(dummy)
        self.assertTrue(IWorkflow.providedBy(wf_obj))

    def test_remove_wf(self):
        wfs = self.config.registry.workflows
        wfs.set_wf('Document', 'simple_workflow')
        self.assertEqual(wfs.get_wf('Document'), 'simple_workflow')
        wfs.set_wf('Document', None)
        self.assertEqual(wfs.get_wf('Document'), None)

    def test_do_transition(self):
        from arche.models.workflow import get_context_wf
        self.config.set_content_workflow('Dummy', 'simple_workflow')
        dummy = _mk_dummy()
        wf = get_context_wf(dummy)
        wf.do_transition('private:public')

    def test_do_transiton_events(self):
        from arche.models.workflow import get_context_wf
        self.config.set_content_workflow('Dummy', 'simple_workflow')
        dummy = _mk_dummy()
        wf = get_context_wf(dummy)
        before_events = []
        after_events = []
        def before_s(obj, event):
            before_events.append(event.workflow.state)
        def after_s(obj, event):
            after_events.append(event.workflow.state)
        self.config.add_subscriber(before_s, [IContextACL, IWorkflowBeforeTransition])
        self.config.add_subscriber(after_s, [IContextACL, IWorkflowAfterTransition])
        wf.do_transition('private:public')
        self.assertEqual(before_events[0], 'private')
        self.assertEqual(after_events[0], 'public')

    def test_read_paster_conf(self):
        from arche.models.workflow import read_paster_wf_config
        self.config.registry.settings['arche.workflows'] = "\n  Root\nDocument simple_workflow\n"
        read_paster_wf_config(self.config)
        wfs = self.config.registry.workflows
        self.assertEqual(wfs.get_wf('Document'), 'simple_workflow')
        self.assertEqual(wfs.get_wf('Root'), None)


class WfUtilsTests(TestCase):

    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())
        self.config.include('arche.testing')
 
    def tearDown(self):
        testing.tearDown()

    def test_get_context_wf_no_wfs(self):
        from arche.models.workflow import get_context_wf
        dummy = _mk_dummy()
        self.assertEqual(get_context_wf(dummy), None)

