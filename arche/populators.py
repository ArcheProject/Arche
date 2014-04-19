from arche.utils import get_content_factories
from arche.security import get_local_roles
from arche.security import ROLE_ADMIN
from arche import _
        

def root_populator(title = u"", userid = u"", email = u"", password = u""):
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
    description = _(u"Group for all administrators. Add any administrators to this group.")
    groups['administrators'] = adm_group = factories['Group'](title = _(u"Administrators"),
                                                              description = description,
                                                              members = [userid])
    #Add admin role
    local_roles = get_local_roles(root)
    local_roles[adm_group.principal_name] = (ROLE_ADMIN,)
    return root
