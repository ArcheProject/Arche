from __future__ import unicode_literals

from itertools import islice

from pyramid.httpexceptions import HTTPBadRequest

from repoze.catalog.query import Eq
from repoze.catalog.query import Contains

from arche import _
from arche import security
from arche.fanstatic_lib import users_groups_js
from arche.interfaces import IJSONData
from arche.views.base import BaseView


class UsersView(BaseView):
    """ A table listing of all users.
    """

    def __call__(self):
        users_groups_js.need()
        return {
            'fields': (
                ('userid', _('UserID')),
                ('email', _('Email')),
                ('first_name', _('First name')),
                ('last_name', _('Last name')),
                ('created', _('Created')),
            ),
        }


class JSONUsers(BaseView):

    def __call__(self):
        query = Eq('type_name', 'User') & Eq('path', self.request.resource_path(self.context))
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
        # Slice off some?
        docids = islice(docids, start, start+limit)
        users = self.request.resolve_docids(docids)
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
    config.add_view(UsersView,
                    name = 'view',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "arche:templates/content/users_table.pt",
                    context = 'arche.interfaces.IUsers')
    config.add_view(JSONUsers,
                    name = 'users.json',
                    permission = security.PERM_MANAGE_USERS,
                    renderer = "json",
                    context = 'arche.interfaces.IUsers')
