from pyramid.httpexceptions import HTTPFound

from arche import security
from arche.interfaces import IContextACL
from arche.views.base import BaseView
from arche.models.workflow import get_context_wf


class WorkflowTransitionView(BaseView):

    def __call__(self):
        transition_id = self.request.GET.get('id')
        wf = get_context_wf(self.context, self.request.registry)
        transition = wf.do_transition(transition_id)
        if transition.message:
            self.flash_messages.add(transition.message)
        return_url = self.request.GET.get('return_url')
        return HTTPFound(location = return_url)


def includeme(config):
    config.add_view(WorkflowTransitionView,
                    context = IContextACL,
                    name = '__wf_transition__',
                    permission = security.NO_PERMISSION_REQUIRED) #Permission is checked by the method do_transition
