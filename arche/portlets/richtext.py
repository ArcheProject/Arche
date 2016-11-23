from __future__ import unicode_literals

import colander
import deform
from pyramid.renderers import render

from arche.portlets import PortletType
from arche import _


@colander.deferred
def richtext_title(node, kw):
    request = kw['request']
    return request.localizer.translate(_("Richtext"))


class RichtextPortletSchema(colander.Schema):
    title = colander.SchemaNode(
        colander.String(),
        title = _("Title"),
        description = _("Shown in portlet manager"),
        default = richtext_title,
    )
    body = colander.SchemaNode(
        colander.String(),
        title = _("Body"),
        widget = deform.widget.RichTextWidget(height=300),
    )
    show_container = colander.SchemaNode(
        colander.Boolean(),
        title = _("Show portlet panel"),
        description = _("show_container_description",
                        default = "If this is inactive, only the richtext (body) "
                                  "content will be rendered."),
        default = True,
    )
    hide_in_subfolders = colander.SchemaNode(
        colander.Boolean(),
        title = _("Hide in subfolders"),
        description = _("Only render in this context."),
    )


class RichtextPortlet(PortletType):
    name = "richtext"
    schema_factory = RichtextPortletSchema
    title = _("Richtext")

    def render(self, context, request, view, **kwargs):
        settings = self.portlet.settings
        if settings.get('hide_in_subfolders', False) and context != self.context:
            return
        values = {'title': settings.get('title', self.title),
                  'body': settings.get('body',''),
                  'show_container': settings.get('show_container', True),
                  'portlet': self.portlet}
        return render("arche:templates/portlets/richtext.pt",
                      values,
                      request = request)


def includeme(config):
    config.add_portlet(RichtextPortlet)