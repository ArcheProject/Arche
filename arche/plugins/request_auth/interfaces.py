from arche.interfaces import IContextAdapter


class IRequestSession(IContextAdapter):
    """ Request an auth session for remote users.
    """

    def new(request, userid, client_ip='', login_max_valid=30,
            link_valid=20, redirect_url=''):
        """ Create a new session. Will return the link to activate it.
        """

    def new_from_request(request):
        """ Use post data in the request to crate a new auth link.
        """

    def get_data(request):
        """ Fetch post data from the request. Raises colander.Invalid
            if the data isn't valid.
        """

    def consume(request, userid):
        """ Consume the link. Post-validation function
            to simply return the redirect and fire all events.
        """

    def consume_from_request(request):
        """ Validates and extracts info from request.POST. Then calls consume.
        """
