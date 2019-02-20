from __future__ import unicode_literals

from arche import _
from arche.security import ROLE_ADMIN
from arche.utils import get_content_factories
from pyramid.threadlocal import get_current_request


def root_populator(title = "", userid = "", email = "", password = ""):
    factories = get_content_factories()
    root = factories['Root'](title = title)
    #Add users
    root['users'] = users = factories['Users']()
    #Add user
    assert userid
    users[userid] = factories['User'](email = email, password = password)
    #Add groups
    root['groups'] = groups = factories['Groups']()
    #Add administrators group
    description = _("Group with administrative rights.")
    title = _(u"Administrators")
    request = get_current_request()
    if request is not None:
        description = request.localizer.translate(description)
        title = request.localizer.translate(title)
    groups['administrators'] = adm_group = factories['Group'](title = title,
                                                              description = description,
                                                              members = [userid])
    #Add admin role
    root.local_roles[adm_group.principal_name] = (ROLE_ADMIN,)
    return root
