from zope.interface import Interface


class IBase(Interface):
    pass

class IBare(Interface):
    pass

class IContent(Interface):
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

class IGroup(Interface):
    pass

class IGroups(Interface):
    pass

class IRole(Interface):
    pass

class IRoles(Interface):
    """ Adapter for IBase content that stores and fetches assigned roles. """
