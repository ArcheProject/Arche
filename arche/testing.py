from pyramid.authentication import CallbackAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid_mailer.interfaces import IMailer
from zope.interface import implementer


def barebone_fixture(config):
    from arche.api import Root
    from arche.api import Users
    root = Root()
    root['users'] = Users()
    return root

def setup_auth(config, userid = None, debug = True):
    from arche.security import groupfinder
    config.set_authorization_policy(ACLAuthorizationPolicy())
    ap = CallbackAuthenticationPolicy()
    ap.debug = debug
    ap.unauthenticated_userid = lambda request: userid
    ap.callback = groupfinder
    config.set_authentication_policy(ap)

def catalog(config):
    """ Include any catalog related things. Include arche.testing first. """
    config.include('arche.models.catalog')

def workflow(config):
    """ Include workflow related things."""
    config.include('arche.models.workflow')

def printing_mailer(config):
    """ Temporary: This is only while waiting for the release of pyramid_mailer's debug mode. """
    print "\nWARNING! Using printing mailer - no mail will be sent!\n"
    mailer = PrintingMailer()
    config.registry.registerUtility(mailer)

@implementer(IMailer)
class PrintingMailer(object):
    """
    Dummy mailing instance. Simply prints all messages directly instead of handling them.
    Good for avoiding mailing users when you want to test things locally.
    """

    def send(self, message):
        """
        Print message content instead of sending it
        """
        print "From: %s " % message.sender
        print "Subject: %s" % message.subject
        print "To: %s" % ", ".join(message.recipients)
        print "=== HTML"
        print message.html
        print "=== PLAINTEXT"
        print message.body
        print "---"

    send_to_queue = send_immediately = send


def includeme(config):
    """ Setup minimal basics for running tests. """
    config.include('arche.security')
    config.include('arche.utils')
