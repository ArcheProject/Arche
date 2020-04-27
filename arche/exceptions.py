from arche import _


class WorkflowException(Exception):
    """ Workflow errors.
    """


class CatalogConfigError(Exception):
    """ Catalog index registration has a conflict or error.
    """


class CatalogNeedsUpdate(Exception):
    """ Catalog needs an update, and this should block any startup procedure. """


class EvolverVersionError(Exception):
    """ The version requirement wasn't met.
    """


#FIXME: Add __json__ method
class ReferenceGuarded(Exception):
    msg = ""
    guarded = ()
    context = None

    def __init__(self, context,  ref_guard, message=None, guarded=(), title=_("Reference guarded error")):
        if not message:
            message = _(
                "refguard_default_message",
                default="Refguard vetos delete of ${context}\n"
                        "The following objects (or docids) would stop working as expected:\n"
                        "${ojbs}",
                mapping={'context': str(context), 'objs': "\n".join([str(x) for x in guarded])}
            )
        self.context = context
        self.message = message
        self.guarded = guarded
        self.ref_guard = ref_guard
        self.title = title

    def __str__(self):
        return self.message
