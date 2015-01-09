from uuid import uuid4

from zope.component import adapter
from zope.interface import implementer
from pyramid.interfaces import IRequest
from pyramid.renderers import render

from arche.interfaces import IFlashMessages


@adapter(IRequest)
@implementer(IFlashMessages)
class FlashMessages(object):
    """ See IFlashMessages"""

    def __init__(self, request):
        self.request = request

    def add(self, msg, type='info', dismissable = True, auto_destruct = True):
        css_classes = ['alert']
        css_classes.append('alert-%s' % type)
        if dismissable:
            css_classes.append('alert-dismissable')
        css_classes = " ".join(css_classes)
        flash = {'msg':msg, 'dismissable': dismissable, 'css_classes': css_classes, 'auto_destruct': auto_destruct}
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
