from uuid import uuid4

from zope.component import adapter
from zope.interface import implementer
from pyramid.interfaces import IRequest
from pyramid.renderers import render
import transaction

from arche.interfaces import IFlashMessages


@adapter(IRequest)
@implementer(IFlashMessages)
class FlashMessages(object):
    """ Adapter for flash messages. """

    def __init__(self, request):
        self.request = request

    def add(self, msg, type='info', dismissable = True, auto_destruct = True, require_commit = True):
        """ Add a flash message to the session.
        
            msg
                Text to display.

            type
                The kind of message. Used to construct bootstrap alert classes.
                Good choices are 'success', 'info', 'warning', 'danger'.
            
            auto_destruct
                The message will remove itself.
            
            require_commit
                Make sure the transaction passes before adding the message. (I.e. no flash message
                "Saved successfully" when DB didn't save)

                This is usually a good idea, except for error messages that should be displayed
                when something actually goes wrong.
        """
        css_classes = ['alert']
        css_classes.append('alert-%s' % type)
        if dismissable:
            css_classes.append('alert-dismissable')
        css_classes = " ".join(css_classes)
        flash = {'msg':msg, 'dismissable': dismissable, 'css_classes': css_classes, 'auto_destruct': auto_destruct}
        if require_commit:
            def hook(success):
                if success:
                    self.request.session.flash(flash)
            transaction.get().addAfterCommitHook(hook)
        else:
            self.request.session.flash(flash)

    def get_messages(self):
        for message in self.request.session.pop_flash():
            message['id'] = unicode(uuid4())
            yield message

    def render(self):
        response = {'get_messages': self.get_messages}
        return render("arche:templates/flash_messages.pt", response, request = self.request)


def includeme(config):
    config.registry.registerAdapter(FlashMessages)
