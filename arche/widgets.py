from json import dumps

from colander import null
from deform.widget import Select2Widget
from pyramid.traversal import find_resource
from repoze.catalog.query import Any

                                                  
class ReferenceWidget(Select2Widget):
    """ A reference widget that searches for content to reference.
        It returns a list.
        
        Note! Any default values for this must return an iterator with uids.
        
        
        query_params
            Things to send to search.json page
            glob: 1 is always a good idea, since it enables search with glob
            type_name: Limit to these content types only. Either a list or a single name as a string.
    """
    template = 'widgets/select2_reference'
    readonly_template = 'widgets/select2_reference' #XXX
    null_value = ''
    placeholder = "Type something to search."
    minimumInputLength = 2
    default_query_params = {'glob': 1}
    query_params = {}
    #Make query view configurable?
    
    def _preload_data(self, field, cstruct):
        #XXX: Should this be moved to the json search view and invoked as a subrequest? Maybe
        view = field.schema.bindings['view']
        root = view.root
        query = root.catalog.query
        address_for_docid = root.document_map.address_for_docid
        results = []
        docids = query(Any('uid', cstruct))[1]
        for docid in docids:
            path = address_for_docid(docid)
            obj = find_resource(root, path)
            results.append({'id': obj.uid, 'text': obj.title})
        return dumps(results)

    def serialize(self, field, cstruct, **kw):
        view = field.schema.bindings['view']
        preload_data = "[]"
        if cstruct in (null, None):
            cstruct = self.null_value
        else:
            preload_data = self._preload_data(field, cstruct)
        readonly = kw.get('readonly', self.readonly)
        kw['placeholder'] = kw.get('placeholder', self.placeholder)
        kw['minimumInputLength'] = kw.get('minimumInputLength', self.minimumInputLength)
        query_params = self.default_query_params.copy()
        query_params.update(self.query_params)
        query_url = view.request.resource_url(view.root, 'search.json', query = query_params)
        #FIXME: Support all kinds of keywords that the select2 widget supports?
        template = readonly and self.readonly_template or self.template
        tmpl_values = self.get_template_values(field, cstruct, kw)
        return field.renderer(template, preload_data = preload_data, query_url = query_url, **tmpl_values)

    def deserialize(self, field, pstruct):
        #Make sure pstruct follows query params?
        if pstruct in (null, self.null_value):
            return null
        return tuple(pstruct.split(','))
    