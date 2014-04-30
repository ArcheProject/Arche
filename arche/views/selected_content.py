import colander

from arche.views.base import ContentView
from arche.widgets import ReferenceWidget
from arche import security
from arche import _


class SelectContentSchema(colander.Schema):
    selected_content = colander.SchemaNode(colander.List(),
                                   title = _(u"Select content to show"),
                                   missing = colander.null,
                                   widget = ReferenceWidget())
    show_body = colander.SchemaNode(colander.Bool(),
                                    title = _(u"Show content body, if any"),
                                    )


class SelectedContentView(ContentView):
    title = _('Selected content')
    settings_schema = SelectContentSchema

    def __call__(self):
        contents = []
        for uid in self.settings.get('selected_content', ()):
            #Generator
            for res in self.catalog_search(resolve = True, uid = uid):
                contents.append(res)
        return {'contents': contents}


def includeme(config):
    config.add_view(SelectedContentView,
                    name = 'selected_content_view',
                    permission = security.PERM_VIEW,
                    renderer = "arche:templates/content/selected_content.pt",
                    context = 'arche.interfaces.IBase')
    config.add_content_view('Document', 'selected_content_view', SelectedContentView)
    config.add_content_view('Root', 'selected_content_view', SelectedContentView)
