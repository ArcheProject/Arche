from arche.models.workflow import Workflow
from arche import _
from arche import security


class ActivateWorkflow(Workflow):
    """ Technical on/off workflow."""
    name = 'activate_workflow'
    title = _("Activate workflow")
    description = _("Used for things that should be switched on or off.")
    states = {'enabled': _("Enabled"),
              'disabled': _("Disabled")}
    transitions = {}
    initial_state = 'disabled'

    @classmethod
    def init_acl(cls, registry):
        aclreg = registry.acl
        #Enabled
        enabled_name = "%s:enabled" % cls.name
        enabled = aclreg.new_acl(enabled_name, title = _("Enabled"))
        enabled.add(security.ROLE_ADMIN, security.ALL_PERMISSIONS)
        enabled.add(security.ROLE_EDITOR, [security.PERM_VIEW, security.PERM_EDIT])
        #Disabled
        disabled_name = "%s:disabled" % cls.name
        disabled = aclreg.new_acl(disabled_name, title = _("Disabled"))
        disabled.add(security.ROLE_ADMIN, security.ALL_PERMISSIONS)
        disabled.add(security.ROLE_EDITOR, [security.PERM_VIEW, security.PERM_EDIT])


ActivateWorkflow.add_transitions(
    from_states='enabled',
    to_states='disabled',
    title = _("Disable"),
    permission=security.PERM_EDIT

)

ActivateWorkflow.add_transitions(
    from_states='disabled',
    to_states='enabled',
    title = _("Enable"),
    permission=security.PERM_EDIT
)


def includeme(config):
    config.add_workflow(ActivateWorkflow)
