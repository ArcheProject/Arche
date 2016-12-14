from uuid import uuid4

from zope.component import adapter
from zope.interface import implementer
from pyramid.interfaces import IRequest
from pyramid.renderers import render
import transaction
from six import text_type

from arche.interfaces import IFlashMessages


@adapter(IRequest)
@implementer(IFlashMessages)
class FlashMessages(object):
    """ Adapter for flash messages. """

    def __init__(self, request):
        self.request = request

    def add(self, msg, type='info', auto_destruct = None, require_commit = True, icon_class = None):
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

            icon_class
                If set, render a span with this class(es). For instance, set 'glyphicon glyphicon-ok'
                will render '<span class="glyphicon glyphicon-ok"></span>'.
        """
        flash = {'msg':msg, 'type': type, 'icon_class': icon_class}
        if auto_destruct != None:
            flash['auto_destruct'] = auto_destruct
        if require_commit:
            def hook(success):
                if success:
                    self.request.session.flash(flash, allow_duplicate=False)
            transaction.get().addAfterCommitHook(hook)
        else:
            self.request.session.flash(flash, allow_duplicate=False)

    def get_messages(self):
        for message in self.request.session.pop_flash():
            message['id'] = text_type(uuid4())
            yield message

    def render(self):
        #DEPRECATED
        response = {'get_messages': self.get_messages}
        return render("arche:templates/flash_messages.pt", response, request = self.request)


def includeme(config):
    config.registry.registerAdapter(FlashMessages)
