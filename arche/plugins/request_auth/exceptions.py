

class ConsumeTokenError(Exception):
    """ Raised when consuming a token went wrong.
        Usually caught by views so a HTTPBadRequest is sent instead.
    """
