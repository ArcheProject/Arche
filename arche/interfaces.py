from zope.interface import Interface


class IBase(Interface):
    pass

class IUser(IBase):
    pass

class IUsers(Interface):
    pass

class IFlashMessages(Interface):
    pass

class IRoot(Interface):
    """ Marker interface for the site root."""

class IInitialSetup(Interface):
    """ For populating the site."""


class IGroups(Interface):
    """ Adapter for root that stores and fetches groups. """
    #FIXME: Not implemented yet!

class IRoles(Interface):
    """ Adapter for IBase content that stores and fetches assigned roles. """
