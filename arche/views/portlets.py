from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPForbidden
from pyramid.httpexceptions import HTTPFound
from pyramid.httpexceptions import HTTPNotFound
import colander
import deform

from arche import _
from arche import security
from arche.fanstatic_lib import manage_portlets_js
from arche.interfaces import IContent
from arche.interfaces import IFlashMessages
from arche.portlets import get_available_portlets
from arche.portlets import get_portlet_manager
from arche.portlets import get_portlet_slots
from arche.views.base import button_add
from arche.views.base import BaseForm
from arche.views.base import BaseView


class ManagePortlets(BaseView):

    @reify
    def slots(self):
        return get_portlet_slots(self.request.registry)

    def get_form(self, slot_name, slotinfo):
        values = [('', _('<Select>'))]
        translate = self.request.localizer.translate
        for (name, title) in get_available_portlets(self.request.registry):
            full_title = u"%s (%s)" % (translate(title), name)
            values.append((name, full_title))

        class AddPortlet(colander.Schema):
            portlet_type = colander.SchemaNode(colander.String(),
                                               title = _(u"Type"),
                                               widget = deform.widget.SelectWidget(values = values))
        schema = AddPortlet()
        add_url = self.request.resource_url(self.context, 'add_portlet', query = {'slot': slot_name})
        return deform.Form(schema, buttons = (button_add,), action = add_url)

    @property
    def forms(self):
        forms = {}
        for (name, slotinfo) in self.slots.items():
            forms[name] = self.get_form(name, slotinfo)
        return forms

    def __call__(self):
        manage_portlets_js.need()
        custom_slots = set(self.slots.keys()) - set(['right', 'left', 'top', 'bottom'])
        return {'slots': self.slots,
                'custom_slots': custom_slots,
                'portlet_manager': get_portlet_manager(self.context, self.request.registry)}


class SavePortletSlotOrder(BaseView):

    @reify
    def slots(self):
        return get_portlet_slots(self.request.registry)

    @reify
    def manager(self):
        return get_portlet_manager(self.context, self.request.registry)

    def __call__(self):
        slotname = self.request.subpath[0]
        slot = self.manager[slotname]
        new_order = self.request.POST.getall('uids[]')
        if set(new_order) != set(slot.keys()):
            raise HTTPForbidden("Sorting contained wrong length of items. You may need to reload this page.")
        slot.order = new_order
        return {}


def add_portlet(context, request):
    slot = request.GET['slot']
    portlet_type = request.POST['portlet_type']
    manager = get_portlet_manager(context)
    portlet = manager.add(slot, portlet_type)
    settings_schema = getattr(portlet, 'schema_factory', None)
    if settings_schema:
        url = request.resource_url(context, 'edit_portlet', query = {'slot': slot, 'portlet': portlet.uid})
    else:
        fm = IFlashMessages(request)
        fm.add(_("Added"))
        url = request.resource_url(context, 'manage_portlets')
    return HTTPFound(location = url)


def delete_portlet(context, request):
    slot = request.GET['slot']
    portlet_uid = request.GET['portlet']
    manager = get_portlet_manager(context)
    manager.remove(slot, portlet_uid)
    url = request.resource_url(context, 'manage_portlets')
    return HTTPFound(location = url)


def enable_portlet_toggle(context, request):
    slot = request.GET['slot']
    portlet_uid = request.GET['portlet']
    manager = get_portlet_manager(context)
    try:
        portlet = manager[slot][portlet_uid]
    except KeyError:
        raise HTTPNotFound()
    #Toggle
    portlet.enabled = not portlet.enabled
    url = request.resource_url(context, 'manage_portlets')
    return HTTPFound(location = url)


class EditPortlet(BaseForm):

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
        return _(u"Edit ${portlet_title}",
                 mapping = {'portlet_title': self.request.localizer.translate(self.portlet.title)})

    def get_schema(self):
        factory = getattr(self.portlet, 'schema_factory', None)
        if factory:
            return self.portlet.schema_factory
        else:
            raise HTTPForbidden(_("Nothing to edit for this portlet"))

    def appstruct(self):
        return dict(self.portlet.settings)

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        self.portlet.settings = appstruct
        return HTTPFound(location = self.request.resource_url(self.context, 'manage_portlets'))

    def cancel_success(self, *args):
        super(EditPortlet, self).cancel()
        return HTTPFound(location = self.request.resource_url(self.context, 'manage_portlets'))


def includeme(config):
    config.add_view(ManagePortlets,
                    context = IContent,
                    name = 'manage_portlets',
                    permission = security.PERM_MANAGE_SYSTEM,
                    renderer = 'arche:templates/manage_portlets.pt')
    config.add_view(SavePortletSlotOrder,
                    context = IContent,
                    name = '__save_portlet_slot_order__',
                    permission = security.PERM_MANAGE_SYSTEM,
                    renderer = 'json')
    config.add_view(add_portlet,
                    context = IContent,
                    name = 'add_portlet',
                    permission = security.PERM_MANAGE_SYSTEM)
    config.add_view(delete_portlet,
                    context = IContent,
                    name = 'delete_portlet',
                    permission = security.PERM_MANAGE_SYSTEM)
    config.add_view(enable_portlet_toggle,
                    context = IContent,
                    name = 'enable_portlet_toggle',
                    permission = security.PERM_MANAGE_SYSTEM)
    config.add_view(EditPortlet,
                    context = IContent,
                    name = 'edit_portlet',
                    renderer = u'arche:templates/form.pt',
                    permission = security.PERM_MANAGE_SYSTEM)
