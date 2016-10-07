

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
