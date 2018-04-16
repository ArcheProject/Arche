from arche import _


class WorkflowException(Exception):
    """ Workflow errors.
    """


class CatalogError(Exception):
    """ Something went wrong when registering catalog indexes.
        Usually solved with updating the catalog from the script that should be in bin.
    """
    def __init__(self, msg):
        msg += "\nTry updating the catalog with the console script 'bin/arche <paster.ini file> create_catalog'. " \
               "If you're on a development instance, you may set the 'arche.auto_recreate_catalog' setting to true."
        super(CatalogError, self).__init__(msg)


class CatalogConfigError(Exception):
    """ Catalog index registration has a conflict or error.
    """


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
