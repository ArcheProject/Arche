from zope.interface import Interface


class IAuthSessionData(Interface):
    """ Keeps track of session related data like login and IP.
    """
