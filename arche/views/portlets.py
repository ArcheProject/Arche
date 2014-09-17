import deform
import colander
from pyramid.httpexceptions import HTTPFound
from pyramid.decorator import reify

from arche.views.base import BaseForm, BaseView
from arche.interfaces import IContent
from arche.portlets import (get_portlet_slots,
                            get_portlet_manager,
                            get_available_portlets)

from arche import security
from arche import _


button_add = deform.Button('add', title = _(u"Add"), css_class = 'btn btn-primary')


class ManagePortlets(BaseView):

    @reify
    def slots(self):
        return get_portlet_slots(self.request.registry)

    def get_form(self, name, slotinfo):
        values = [('', _('<Select>'))]
        values.extend(get_available_portlets(self.request.registry))

        class AddPortlet(colander.Schema):
            portlet_type = colander.SchemaNode(colander.String(),
                                               title = _(u"Type"),
                                               widget = deform.widget.SelectWidget(values = values))
        schema = AddPortlet()
        add_url = self.request.resource_url(self.context, 'add_portlet', query = {'slot': name})
        return deform.Form(schema, buttons = (button_add,), action = add_url)
    
    def __call__(self):
        forms = {}
        for (name, slotinfo) in self.slots.items():
            forms[name] = self.get_form(name, slotinfo)
        return {'slots': self.slots, 'forms': forms,
                'portlet_manager': get_portlet_manager(self.context, self.request.registry)}


def add_portlet(context, request):
    slot = request.GET['slot']
    portlet_type = request.POST['portlet_type']
    manager = get_portlet_manager(context)
    portlet = manager.add(slot, portlet_type)
    url = request.resource_url(context, 'edit_portlet', query = {'slot': slot, 'portlet': portlet.uid})
    return HTTPFound(location = url)
    
def delete_portlet(context, request):
    slot = request.GET['slot']
    portlet_uid = request.GET['portlet']
    manager = get_portlet_manager(context)
    manager.remove(slot, portlet_uid)
    url = request.resource_url(context, 'manage_portlets')
    return HTTPFound(location = url)


class EditPortlet(BaseForm):

    def __call__(self):
        factory = getattr(self.portlet, 'schema_factory', None)
        if factory:
            self.schema = self.portlet.schema_factory()
            return super(EditPortlet, self).__call__()
        #XXXX: NOthing to edit message?
        return HTTPFound(location = self.request.resource_url(self.context, 'manage_portlets'))

    def appstruct(self):
        return dict(self.portlet.settings)

    @property
    def portlet(self):
        slot = self.request.GET['slot']
        portlet_uid = self.request.GET['portlet']
        slot_portlets = self.portlet_manager.get(slot, {})
        return slot_portlets.get(portlet_uid, None)

    @property
    def portlet_manager(self):
        return get_portlet_manager(self.context, self.request.registry)

    @property
    def title(self):
        return _(u"Edit portlet")

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        self.portlet.settings = appstruct
        return HTTPFound(location = self.request.resource_url(self.context, 'manage_portlets'))


def includeme(config):
    config.add_view(ManagePortlets,
                    context = IContent,
                    name = 'manage_portlets',
                    permission = security.PERM_MANAGE_SYSTEM,
                    renderer = 'arche:templates/manage_portlets.pt')
    config.add_view(add_portlet,
                    context = IContent,
                    name = 'add_portlet',
                    permission = security.PERM_MANAGE_SYSTEM)
    config.add_view(delete_portlet,
                    context = IContent,
                    name = 'delete_portlet',
                    permission = security.PERM_MANAGE_SYSTEM)
    config.add_view(EditPortlet,
                    context = IContent,
                    name = 'edit_portlet',
                    renderer = u'arche:templates/form.pt',
                    permission = security.PERM_MANAGE_SYSTEM)
