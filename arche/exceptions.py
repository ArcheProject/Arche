

class WorkflowException(Exception):
    """ Workflow errors.
    """


class CatalogError(Exception):
    """ Something went wrong when registering catalog indexes.
        Usually solved with updating the catalog from the script that should be in bin.
    """
    def __init__(self, msg):
        msg += "\nTry updating the catalog with the console script."
        super(CatalogError, self).__init__(msg)


class EvolverVersionError(Exception):
    """ The version requirement wasn't met.
    """
