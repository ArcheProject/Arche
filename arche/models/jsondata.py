from zope.component import adapter
from zope.interface import implementer

from arche.interfaces import IBase, IContextACL
from arche.interfaces import IFolder
from arche.interfaces import IJSONData
from pyramid.i18n import TranslationString


@implementer(IJSONData)
@adapter(IBase)
class JSONData(object):
    """ Adater for creating json data from an IBase object.
        This is a prototype and might not be included later on.
    """

    def __init__(self, context):
        self.context = context

    def __call__(self, request, dt_formater = None, attrs = (), dt_atts = ()):
        normal_attrs = ['description', 'type_name',
                        'type_title', 'uid',
                        '__name__', 'size', 'mimetype']
        normal_attrs.extend(attrs)
        dt_attrs = ['created', 'modified']
        dt_attrs.extend(dt_attrs)
        #wf_state and name?
        results = {}
        if IContextACL.providedBy(self.context) and self.context.workflow != None:
            results['wf_state'] = self.context.wf_state
            results['workflow'] = self.context.workflow.name
        else:
            results['wf_state'] = ""
            results['workflow'] = ""
        results['css_icon'] = getattr(self.context, 'css_icon', '')
        results['tags'] = tuple(getattr(self.context, 'tags', ()))
        results['is_folder'] = IFolder.providedBy(self.context)
        title = getattr(self.context, 'title', None)
        if not title:
            title = self.context.__name__
        results['title'] = title
        for attr in normal_attrs:
            results[attr] = getattr(self.context, attr, '')
            if isinstance(results[attr], TranslationString):
                results[attr] = request.localizer.translate(results[attr])
        for attr in dt_attrs:
            val = getattr(self.context, attr, '')
            if val and dt_formater:
                results[attr] = request.localizer.translate(dt_formater(val))
            else:
                results[attr] = val
        return results


def includeme(config):
    config.registry.registerAdapter(JSONData)
