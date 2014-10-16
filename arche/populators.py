from __future__ import unicode_literals

from zope.component import adapter
from zope.interface import implementer
from pyramid.threadlocal import get_current_registry

from arche import _
from arche.interfaces import IPopulator
from arche.interfaces import IRoot
from arche.security import ROLE_ADMIN
from arche.security import get_local_roles
from arche.utils import get_content_factories
from arche.workflow import WorkflowException
from arche.workflow import get_context_wf


def root_populator(title = "", userid = "", email = "", password = "", populator_name = ""):
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
    #Run extra populator
    if populator_name:
        reg = get_current_registry()
        populator = reg.getAdapter(root, IPopulator, name = populator_name)
        populator.populate()
    #Publish root
    try:
        wf = get_context_wf(root)
        wf.do_transition('private:public', force = True)
    except WorkflowException:
        pass
    return root


@implementer(IPopulator)
@adapter(IRoot)
class Populator(object):
    name = ""
    title = ""
    description = ""

    def __init__(self, context):
        self.context = context

    def populate(self, **kw):
        raise NotImplementedError()


# class ExampleContentPopulator(Populator):
#     name = "example_content"
#     title = _("Example content")
#     description = _("Gives you some content to play with from start")
# 
#     def populate(self, **kw):
#         pass


def add_populator(config, populator):
    #Check interfaces etc?
    config.registry.registerAdapter(populator, name = populator.name)


def includeme(config):
    config.add_directive('add_populator', add_populator)
    #config.add_populator(ExampleContentPopulator)
