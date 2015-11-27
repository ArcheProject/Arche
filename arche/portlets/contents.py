from __future__ import unicode_literals

from pyramid.renderers import render

from arche.portlets import PortletType
from arche import _
from arche.security import PERM_VIEW


class ContentsPortlet(PortletType):
    name = "contents"
    schema_factory = None
    title = _(u"Contents")

    def render(self, context, request, view, **kwargs):
        if context != self.context:
            return
        #FIXME: Implement batching on really large folders
        contents = []
        for obj in context.values():
            if request.has_permission(PERM_VIEW, obj):
                contents.append(obj)
        return render("arche:templates/portlets/contents.pt",
                      {'title': self.title, 'contents': contents, 'portlet': self.portlet},
                      request = request)


def includeme(config):
    config.add_portlet(ContentsPortlet)
