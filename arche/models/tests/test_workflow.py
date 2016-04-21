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

    def _mk_dummy_wf(self):
        class DummyWf(self._cut):
            states = {}
            transitions = {}
            name = 'dummy_wf'
        return DummyWf

    def test_verify_class(self):
        verifyClass(IWorkflow, self._cut)

    def test_verify_object(self):
        verifyObject(IWorkflow, self._cut(_mk_dummy()))

    def test_state_title(self):
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.states['one'] = 'Hello'
        obj.initial_state = 'one'
        self.assertEqual(obj.state_title, 'Hello')

    def test_get_transitions(self):
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.initial_state = 'current'
        one = _mk_dummy_transition()
        two = _mk_dummy_transition(from_state = 'other')
        obj.transitions[one.name] = one
        obj.transitions[two.name] = two
        self.assertEqual(tuple(obj.get_transitions()), (one,))

    def test_get_transitions_wrong_perm(self):
        self.config.testing_securitypolicy('userid', permissive = False)
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.initial_state = 'current'
        one = _mk_dummy_transition()
        two = _mk_dummy_transition(from_state = 'other')
        obj.transitions['one'] = one
        obj.transitions['two'] = two
        self.assertEqual(tuple(obj.get_transitions()), ())

    def test_do_transition(self):
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.initial_state = 'current'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one:future'] = one
        obj.do_transition('one:future')
        self.assertEqual(obj.state, 'future')

    def test_do_transition_wrong_transition(self):
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.initial_state = 'other'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one:future'] = one
        self.assertRaises(ValueError, obj.do_transition, 'one:future')

    def test_do_transition_force_wrong_initial_state(self):
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.initial_state = 'other'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one:future'] = one
        obj.do_transition('one:future', force = True)
        self.assertEqual(obj.state, 'future')

    def test_do_transition_force_wrong_perm(self):
        self.config.testing_securitypolicy('userid', permissive = False)
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.initial_state = 'current'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one:future'] = one
        obj.do_transition('one:future', force = True)
        self.assertEqual(obj.state, 'future')

    def test_do_transition_wrong_perm(self):
        self.config.testing_securitypolicy('userid', permissive = False)
        wf =  self._mk_dummy_wf()
        obj = wf(_mk_dummy())
        obj.initial_state = 'current'
        obj.states['future'] = 'x'
        one = _mk_dummy_transition()
        obj.transitions['one:future'] = one
        self.assertRaises(HTTPForbidden, obj.do_transition, 'one:future')

    def test_add_tranistions_one(self):
        wf = self._mk_dummy_wf()
        wf.states = {'private': '', 'published': ''}
        wf.add_transitions(from_states = 'private', to_states = 'published')
        self.assertEqual(len(wf.transitions), 1)

    def test_add_tranistions_many_to(self):
        wf = self._mk_dummy_wf()
        wf.states = {'private': '', 'published': '', 'pending': ''}
        wf.add_transitions(from_states = 'private', to_states = ('published', 'pending'))
        self.assertEqual(len(wf.transitions), 2)

    def test_add_tranistions_many_from(self):
        wf = self._mk_dummy_wf()
        wf.states = {'private': '', 'published': '', 'pending': ''}
        wf.add_transitions(from_states = ('published', 'pending'), to_states = 'private')
        self.assertEqual(len(wf.transitions), 2)

    def test_add_tranistions_all(self):
        wf = self._mk_dummy_wf()
        wf.states = {'private': '', 'published': '', 'pending': ''}
        wf.add_transitions(from_states = 'private', to_states = '*')
        self.assertEqual(len(wf.transitions), 3)

    def test_add_tranistions_all2(self):
        wf = self._mk_dummy_wf()
        wf.states = {'private': '', 'published': '', 'pending': ''}
        wf.add_transitions(from_states = '*', to_states = '*')
        self.assertEqual(len(wf.transitions), 9)

    def test_add_transitions_create(self):
        wf = self._mk_dummy_wf()
        wf.states = {'one': ''}
        wf.add_transitions(from_states = '*', to_states = 'two', create_states=True)
        self.assertEqual(len(wf.transitions), 1)

    def test_add_transitions_dont_create(self):
        wf = self._mk_dummy_wf()
        self.assertRaises(KeyError, wf.add_transitions, from_states = 'one', to_states = 'two')

    def test_add_transitions_nothing_to_do(self):
        wf = self._mk_dummy_wf()
        self.assertRaises(ValueError, wf.add_transitions, from_states = '*', to_states = '*')


class WorkflowIntegrationTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())
        self.config.include('arche.testing')
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
        self.assertEqual(wf.state, 'public')

    def test_do_transition_expected_state_as_name(self):
        from arche.models.workflow import get_context_wf
        self.config.set_content_workflow('Dummy', 'simple_workflow')
        dummy = _mk_dummy()
        wf = get_context_wf(dummy)
        wf.do_transition('public')
        self.assertEqual(wf.state, 'public')

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

    def test_bulk_state_change(self):
        from arche.models.workflow import bulk_state_change
        from arche.models.workflow import get_context_wf
        from arche.api import Root
        from arche.resources import Document
        self.config.include('arche.models.catalog')
        self.config.include('arche.models.workflow')
        self.config.set_content_workflow('Document', 'simple_workflow')
        root = Root()
        root['d1'] = Document()
        root['d2'] = Document()
        bulk_state_change(root, 'private', 'public')
        self.assertEqual(get_context_wf(root['d1']).state, 'public')
        self.assertEqual(get_context_wf(root['d2']).state, 'public')
