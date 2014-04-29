from json import dumps

from colander import null
from deform.widget import Select2Widget
from pyramid.traversal import find_resource
from repoze.catalog.query import Any

                                                  
class ReferenceWidget(Select2Widget):
    """ A reference widget that searches for content to reference.
        It returns a list.
    """
    template = 'widgets/select2_reference'
    readonly_template = 'widgets/select2_reference' #XXX
    null_value = ''
    placeholder = "Type something to search."
    minimumInputLength = 2

    def _preload_data(self, field, cstruct):
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
        preload_data = "[]"
        if cstruct in (null, None):
            cstruct = self.null_value
        else:
            preload_data = self._preload_data(field, cstruct)
        readonly = kw.get('readonly', self.readonly)
        kw['placeholder'] = kw.get('placeholder', self.placeholder)
        kw['minimumInputLength'] = kw.get('minimumInputLength', self.minimumInputLength)
        #FIXME: Support all kinds of keywords that the select2 widget supports?
        template = readonly and self.readonly_template or self.template
        tmpl_values = self.get_template_values(field, cstruct, kw)
        return field.renderer(template, preload_data = preload_data, **tmpl_values)

    def deserialize(self, field, pstruct):
        if pstruct in (null, self.null_value):
            return null
        return tuple(pstruct.split(','))
    