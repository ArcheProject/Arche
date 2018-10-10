from __future__ import unicode_literals

from deform_autoneed import need_lib
from pyramid.httpexceptions import HTTPBadRequest
from pyramid.httpexceptions import HTTPConflict
from pyramid.httpexceptions import HTTPNoContent
from pyramid.view import view_defaults, view_config
from repoze.catalog.query import Eq
from repoze.catalog.query import Contains
from repoze.catalog.query import Any

from arche.fanstatic_lib import users_groups_js
from arche.interfaces import IJSONData
from arche.views.base import DefaultEditForm
from arche.views.base import DynamicView
from arche.views.base import BaseView
from arche import security
from arche import _


class GroupsView(BaseView):

    def __call__(self):
        return {'contents': [x for x in self.context.values()]}


@view_defaults(context="arche.interfaces.IGroup",
               permission=security.PERM_MANAGE_USERS)
class GroupView(BaseView):

    @view_config(name='view',
                 renderer='arche:templates/content/group.pt')
    def view(self):
        users_groups_js.need()
        need_lib('select2')
        return {
            'fields': (
                ('userid', _('UserID')),
                ('email', _('Email')),
                ('first_name', _('First name')),
                ('last_name', _('Last name')),
                ('created', _('Created')),
            ),
        }

    @property
    def requested_user(self):
        try:
            return self.request.root['users'][self.request.POST['userid']]
        except IndexError:
            raise HTTPBadRequest('No such user')

    @view_config(name='add_user')
    def add_user(self):
        user = self.requested_user
        members = self.context.members
        if user.userid in members:
            raise HTTPConflict(body='User {} already in group.'.format(user.userid))
        members.add(user.userid)
        return HTTPNoContent()

    @view_config(name='remove_user')
    def remove_user(self):
        user = self.requested_user
        members = self.context.members
        if user.userid not in members:
            raise HTTPConflict(body='User {} not in group.'.format(user.userid))
        members.remove(user.userid)
        return HTTPNoContent()


class JSONUsers(BaseView):

    def __call__(self):
        query = Eq('type_name', 'User') & Any('userid', self.context.members)
        q = self.request.GET.get('q')
        if q:
            q = ' '.join([w+'*' for w in q.split()])
            query &= Contains('searchable_text', q)
        result, docids = self.request.root.catalog.query(
            query,
            sort_index=self.request.GET.get('order', 'userid'),
            reverse=self.request.GET.get('reverse') == 'true'
        )
        try:
            start = int(self.request.GET.get('start', 0))
            limit = int(self.request.GET.get('limit', 100))
        except ValueError:
            raise HTTPBadRequest()
        users = self.request.resolve_docids(list(docids)[start:start+limit])
        return {
            'items': self.json_format_objects(users),
            'total': result.total,
        }

    def json_format_objects(self, items):
        res = []
        for obj in items:
            adapted = IJSONData(obj)
            res.append(adapted(
                self.request,
                dt_formater=self.request.dt_handler.format_relative,
                attrs=('userid', 'email', 'first_name', 'last_name', 'email_validated')
            ))
        return res


def includeme(config):
    config.scan(__name__)
    config.add_view(GroupsView,
                    name = 'view',
                    permission = security.PERM_MANAGE_USERS, #FIXME
                    renderer = "arche:templates/content/groups.pt",
                    context = 'arche.interfaces.IGroups')
    config.add_view(DefaultEditForm,
                    name = u"edit",
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "arche:templates/form.pt",
                    context = "arche.interfaces.IGroup")
    # config.add_view(DynamicView,
    #                 context = 'arche.interfaces.IGroup',
    #                 permission = security.PERM_MANAGE_USERS,
    #                 renderer = 'arche:templates/form.pt')
    # config.add_view(GroupView,
    #                 name='view',
    #                 permission=security.PERM_MANAGE_USERS,
    #                 renderer="arche:templates/content/group.pt",
    #                 context='arche.interfaces.IGroup')
    config.add_view(JSONUsers,
                    name='users.json',
                    permission=security.PERM_MANAGE_USERS,
                    renderer="json",
                    context='arche.interfaces.IGroup')
