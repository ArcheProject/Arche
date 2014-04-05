import colander
import deform
from pyramid.traversal import find_root
from pyramid.traversal import lineage
from pyramid.httpexceptions import HTTPFound
from pyramid.decorator import reify
from pyramid.renderers import get_renderer
from pyramid.renderers import render
from pyramid.security import authenticated_userid
from pyramid.security import has_permission
from pyramid_deform import FormView
from deform_autoneed import need_lib

from arche.utils import get_flash_messages
from arche.utils import generate_slug
from arche.fanstatic_lib import main_css
from arche import _


class BaseView(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request
        need_lib('basic')
        main_css.need()

    @reify
    def root(self):
        return find_root(self.context)

    @reify
    def userid(self):
        return authenticated_userid(self.request)

    @reify
    def flash_messages(self):
        return get_flash_messages(self.request)

    def breadcrumbs(self):
        return reversed(list(lineage(self.context)))

    def get_content_factory(self, name):
        return self.request.registry.settings['arche.content_factories'].get(name)

    def macro(self, asset_spec, macro_name='main'):
        return get_renderer(asset_spec).implementation().macros[macro_name]

    def addable_content(self, context):
        #FIXME permisison checks etc
        for factory in self.request.registry.settings['arche.content_factories'].values():
            if getattr(context, 'type_name', None) in getattr(factory, 'addable_to', ()):
                yield factory

    def render_template(self, renderer, **kwargs):
        kwargs.setdefault('view', self)
        return render(renderer, kwargs, self.request)

    def render_actionbar(self, context):
        return self.render_template('arche:templates/action_bar.pt')

    def has_permission(self, permission, context = None):
        #FIXME: Consider other request contexts
        return True #FIXME
        context = context and context or self.context
        return has_permission(permission, context, self.request)


class BaseForm(BaseView, FormView):
    default_success = _(u"Done")
    default_cancel = _(u"Canceled")
    schema_name = u''
    type_name = u''

    button_delete = deform.Button('delete', title = _(u"Delete"), css_class = 'btn btn-danger')
    button_cancel = deform.Button('cancel', title = _(u"Cancel"), css_class = 'btn btn-default')
    button_save = deform.Button('save', title = _(u"Save"), css_class = 'btn btn-primary')
    button_add = deform.Button('add', title = _(u"Add"), css_class = 'btn btn-primary')
    
    buttons = (button_save, button_cancel,)

    def __call__(self):
        self.schema = self.get_schema_factory(self.type_name, self.schema_name)()
        result = super(BaseForm, self).__call__()
#        if isinstance(result, dict):
#            result.update(self.more_template_vars())
        return result

    def get_schema_factory(self, type_name, schema_name):
        return self.request.registry.settings['arche.content_schemas'][type_name][schema_name]

    @property
    def form_options(self):
        return {'action': self.request.url}

    def get_bind_data(self):
        return {'context': self.context, 'request': self.request, 'view': self}

    def appstruct(self):
        appstruct = {}
        for field in self.schema.children:
            if hasattr(self.context, field.name):
                val = getattr(self.context, field.name)
                if val is None:
                    val = colander.null
                appstruct[field.name] = val
        return appstruct

    def cancel(self, *args):
        self.flash_messages.add(self.default_cancel)
        return HTTPFound(location = self.request.resource_url(self.context))
    cancel_success = cancel_failure = cancel


class DefaultAddForm(BaseForm):
    schema_name = u'add'
    header = _(u"Add")

    @property
    def type_name(self):
        return self.request.GET.get('content_type', u'')

    def appstruct(self):
        return {} #Always blank, no data to edit

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        factory = self.get_content_factory(self.type_name)
        obj = factory(**appstruct)
        name = generate_slug(self.context, appstruct['title'])
        self.context[name] = obj
        return HTTPFound(location = self.request.resource_url(obj))


class DefaultEditForm(BaseForm):
    schema_name = u'edit'
    header = _(u"Edit")

    @property
    def type_name(self):
        return self.context.type_name

    def save_success(self, appstruct):
        self.flash_messages.add(self.default_success, type="success")
        self.context.update(**appstruct)
        return HTTPFound(location = self.request.resource_url(self.context))


class DefaultView(BaseView):
    
    def __call__(self):
        return {}


def includeme(config):
    config.add_view(DefaultAddForm,
                    context = 'arche.resources.Base',
                    name = 'add',
                    renderer = 'arche:templates/form.pt')
    config.add_view(DefaultEditForm,
                    context = 'arche.resources.Base',
                    name = 'edit',
                    renderer = 'arche:templates/form.pt')
    config.add_view(DefaultView,
                    context = 'arche.resources.Base',
                    renderer = 'arche:templates/base_view.pt')
