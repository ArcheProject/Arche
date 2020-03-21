from repoze.catalog.query import Eq, Any
from repoze.catalog.query import NotEq

from arche.interfaces import IUser
from arche import _


def find_created_by_user(request, context):
    query = Eq('creator', context.userid) & NotEq('userid', context.userid)
    return request.root.catalog.query(query)


def find_local_roles_for_user(request, context):
    query = Any('local_roles', [context.userid]) & NotEq('userid', context.userid)
    return request.root.catalog.query(query)


def find_groups_for_user(request, context):
    if 'groups' in request.root:
        return list(request.root['groups'].get_users_groups(context.userid))


def find_content_related(request, context):
    query = Any('relation', [context.uid]) & NotEq('uid', context.uid)
    return request.root.catalog.query(query)


def includeme(config):
    config.add_ref_guard(
        find_created_by_user,
        requires=(IUser,),
        catalog_result=True,
        allow_move=False,
        title=_("User listed as creator"),
    )
    config.add_ref_guard(
        find_local_roles_for_user,
        requires=(IUser,),
        catalog_result=True,
        allow_move=False,
        title=_("User has permissions set"),
    )
    config.add_ref_guard(
        find_groups_for_user,
        requires=(IUser,),
        catalog_result=False,
        allow_move=False,
        title=_("User has set permission(s) in group(s)"),
    )
    config.add_ref_guard(
        find_content_related,
        catalog_result=True,
        title=_("Content listed as related (metadata)"),
    )
