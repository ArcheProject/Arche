from __future__ import unicode_literals

from arche import _

import colander
import deform
from pyramid.renderers import render

from arche.interfaces import IContextACL
from arche.interfaces import IRevisions
from arche.interfaces import ITrackRevisions
from arche.models.workflow import get_workflows
from arche.portlets import PortletType


@colander.deferred
def wf_history_title(node, kw):
    request = kw['request']
    return request.localizer.translate(_("Workflow history"))


@colander.deferred
def limit_wfs_widget(node, kw):
    request = kw['request']
    values = []
    for wf in get_workflows(request.registry).values():
        values.append((wf.name, wf.title))
    return deform.widget.CheckboxChoiceWidget(values=values)


class WorkflowHistoryPortletSchema(colander.Schema):
    title = colander.SchemaNode(
        colander.String(),
        title = _("Title"),
        default = wf_history_title,
    )
    limit = colander.SchemaNode(
        colander.Integer(),
        title = _("Only show this amount of entries"),
        default = 5,
    )
    show_wfs = colander.SchemaNode(
        colander.Set(),
        title = _("Enable for these workflows"),
        widget=limit_wfs_widget,
    )


class WorkflowHistoryPortlet(PortletType):
    name = "workflow_history"
    schema_factory = WorkflowHistoryPortletSchema
    title = _("Workflow history")
    tpl = "arche:templates/portlets/workflow_history.pt"

    def visible(self, context, request, view, **kwargs):
        if not ITrackRevisions.providedBy(context):
            return False
        if not IContextACL.providedBy(context):
            return False
        try:
            if not context.workflow.name in self.portlet.settings.get('show_wfs', ()):
                return False
        except AttributeError:
            return False
        revisions = IRevisions(context, None)
        return bool(revisions)

    def render(self, context, request, view, **kwargs):
        if self.visible(context, request, view, **kwargs):
            revisions = IRevisions(context, None)
            limit = self.portlet.settings.get('limit', 5)
            history = tuple(revisions.get_revisions('wf_state', limit = limit))
            if history:
                values = {'title': self.portlet.settings.get('title', self.title),
                          'portlet': self.portlet,
                          'history': history,
                          'workflow': context.workflow,
                          'get_state_title': self.get_state_title,}
                return render(self.tpl,
                              values,
                              request = request)

    def get_state_title(self, workflow, data):
        state = data.get('wf_state', '')
        return workflow.states.get(state, '<Unknown>')


def includeme(config):
    config.add_portlet(WorkflowHistoryPortlet)
