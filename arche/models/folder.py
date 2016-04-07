from arche.interfaces import IArcheFolder
from zope.interface import implementer

from arche.resources import Content, DCMetadataMixin, LocalRolesMixin, ContextACLMixin
from arche import _


@implementer(IArcheFolder)
class ArcheFolder(Content, DCMetadataMixin, LocalRolesMixin, ContextACLMixin):
    """ A generic folder type for creating sections or similar. """
    type_name = u"Folder"
    type_title = _("Folder")
    type_description = _("A generic folder where you may add things.")
    add_permission = "Add %s" % type_name
    css_icon = "glyphicon glyphicon-folder-open"
    nav_visible = True
    listing_visible = True
    search_visible = True


def includeme(config):
    config.add_content_factory(ArcheFolder,
                               addable_in = ['Folder', 'Document', 'Link', 'Image'],
                               addable_to = ['Root'])
