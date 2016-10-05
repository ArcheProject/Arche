from __future__ import unicode_literals

import colander
import deform
from arche.interfaces import IIndexedContent
from arche.models.workflow import get_workflows
from pyramid.renderers import render

from arche.portlets import PortletType
from arche import _
from arche.security import PERM_VIEW


@colander.deferred
def contents_title(node, kw):
    request = kw['request']
    return request.localizer.translate(_("Contents"))


@colander.deferred
def limit_types_widget(node, kw):
    request = kw['request']
    values = []
    for fact in request.content_factories.values():
        if IIndexedContent.implementedBy(fact):
            values.append((fact.type_name, getattr(fact, 'type_title', fact.__class__.__name__)))
    return deform.widget.CheckboxChoiceWidget(values=values)


@colander.deferred
def limit_states_widget(node, kw):
    request = kw['request']
    values = []
    trl = request.localizer.translate
    for wf in get_workflows(request.registry).values():
        for (state, s_title) in wf.states.items():
            title = "%s: %s" % (trl(wf.title), trl(s_title))
            values.append(("%s:%s" % (wf.name, state), title))
    return deform.widget.CheckboxChoiceWidget(values=values)


class ContentsPortletSchema(colander.Schema):
    title = colander.SchemaNode(
        colander.String(),
        title = _("Title"),
        default = contents_title,
    )
    limit_types = colander.SchemaNode(
        colander.Set(),
        title = _("Only show these content types"),
        widget = limit_types_widget,
    )
    limit_states = colander.SchemaNode(
        colander.Set(),
        title = _("Only show these states"),
        widget=limit_states_widget,
    )


class ContentsPortlet(PortletType):
    name = "contents"
    schema_factory = ContentsPortletSchema
    title = _(u"Contents")

    def render(self, context, request, view, **kwargs):
        if context != self.context:
            return
        #FIXME: Implement batching on really large folders
        contents = []
        limit_types = self.portlet.settings.get('limit_types', ())
        limit_states = self.portlet.settings.get('limit_states', ())
        for obj in context.values():
            if not request.has_permission(PERM_VIEW, obj):
                continue
            if limit_types and obj.type_name not in limit_types:
                continue
            if limit_states:
                wf = getattr(obj, 'workflow', '')
                wf_st_name = "%s:%s" % (getattr(wf, 'name', ''), getattr(obj, 'wf_state', ''))
                if wf_st_name not in limit_states:
                    continue
            contents.append(obj)
        if contents:
            values = {'title': self.portlet.settings.get('title', self.title),
                      'contents': contents,
                      'portlet': self.portlet}
            return render("arche:templates/portlets/contents.pt",
                          values,
                          request = request)


def includeme(config):
    config.add_portlet(ContentsPortlet)
