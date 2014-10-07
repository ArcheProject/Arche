from unittest import TestCase

from pyramid import testing
from arche.interfaces import IWorkflow, IWorkflowBeforeTransition, IWorkflowAfterTransition, IContextACL


def _mk_dummy():
    from arche.resources import ContextACLMixin
    class _Dummy(testing.DummyResource, ContextACLMixin):
        type_name = 'Dummy'
    return _Dummy()
    

class WorkflowIntegrationTests(TestCase):
     
    def setUp(self):
        self.config = testing.setUp(request = testing.DummyRequest())
        self.config.include('arche.utils')
        self.config.include('arche.security')
        self.config.include('arche.workflow')
 
    def tearDown(self):
        testing.tearDown()

    def test_set_and_get_wf(self):
        from arche.workflow import get_workflows
        wfs = get_workflows()
        self.assertEqual(wfs.get_wf('Document'), None)
        wfs.set_wf('Document', 'simple_workflow')
        self.assertEqual(wfs.get_wf('Document'), 'simple_workflow')

    def test_get_context_wf(self):
        from arche.workflow import get_workflows
        from arche.workflow import get_context_wf
        wfs = get_workflows()
        dummy = _mk_dummy()
        #self.assertEqual(get_context_wf(dummy), None)
        wfs.set_wf('Dummy', 'simple_workflow')
        wf_obj = get_context_wf(dummy)
        self.assertTrue(IWorkflow.providedBy(wf_obj))

    def test_do_transition(self):
        from arche.workflow import get_workflows, get_context_wf
        wfs = get_workflows()
        wfs.set_wf('Dummy', 'simple_workflow')
        dummy = _mk_dummy()
        wf = get_context_wf(dummy)
        wf.do_transition('private:public')

    def test_do_transiton_events(self):
        from arche.workflow import get_workflows, get_context_wf
        wfs = get_workflows()
        wfs.set_wf('Dummy', 'simple_workflow')
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
