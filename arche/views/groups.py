from pyramid.httpexceptions import HTTPFound

from arche.views.base import DefaultAddForm
from arche.views.base import DefaultEditForm
from arche.views.base import DynamicView
from arche.views.base import BaseView
from arche import security
from arche import _


class GroupsView(BaseView):

    def __call__(self):
        return {'contents': [x for x in self.context.values()]}




def includeme(config):
    config.add_view(GroupsView,
                    name = 'view',
                    permission = security.NO_PERMISSION_REQUIRED, #FIXME
                    renderer = "arche:templates/groups.pt",
                    context = 'arche.interfaces.IGroups')
    config.add_view(DefaultEditForm,
                    name = u"edit",
                    permission = security.PERM_EDIT,
                    renderer = "arche:templates/form.pt",
                    context = "arche.interfaces.IGroup")
    config.add_view(DynamicView,
                    context = 'arche.interfaces.IGroup',
                    permission = security.PERM_EDIT,
                    renderer = 'arche:templates/form.pt')
