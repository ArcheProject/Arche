# -*- coding: utf-8 -*-
from zope.interface import implementer

from arche.plugins.tos.interfaces import ITOS
from arche.resources import Content
from arche.resources import ContextACLMixin


@implementer(ITOS)
class TOS(Content, ContextACLMixin):
    type_name = "TOS"
    type_title = "Terms of service"
    add_permission = 'Add TOS'
    nav_visible = False
    listing_visible = True
    search_visible = False
    title = ""
    body = ""
    revoke_body = ""
    lang = ""
    date = None
    check_password_on_revoke = False
    check_typed_on_revoke = False


def includeme(config):
    config.add_content_factory(TOS, addable_to='Folder')
    config.set_content_workflow('TOS', 'activate_workflow')
