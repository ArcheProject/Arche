from deform_autoneed import resource_registry
from fanstatic import Library
from fanstatic import Resource
from fanstatic.core import render_js
from js.bootstrap import bootstrap_css
from js.bootstrap import bootstrap_js
from js.jquery import jquery
from js.jqueryui import jqueryui
from js.jqueryui import ui_widget
from js.jqueryui import ui_sortable

#Note: A lot of the code here is under developent and review. Don't depend too much on this.

library = Library('arche', 'static')

main_css = Resource(library, 'main.css', depends = (bootstrap_css,))
jquery_file_upload = Resource(library, 'third_party/jquery.fileupload.js', depends=(jquery, ui_widget))

common_js = Resource(library, 'common.js', depends = (jquery,))
touchpunch_js = Resource(library, 'jquery.ui.touch-punch.min.js', depends = (jquery, jqueryui))
manage_portlets_js = Resource(library, 'manage_portlets.js', depends = (common_js,ui_sortable,))
pure_js = Resource(library, 'pure.js', minified = 'pure.min.js', depends = (jquery,))
folderish_contents_js = Resource(library, 'folderish_contents.js',
                                 depends = (pure_js, common_js, ui_sortable, jquery_file_upload))

quill_css = Resource(library, 'quill-1.3.1.snow.css')
quill_js = Resource(library, 'quill-1.3.1.js', depends=(quill_css,))

#IE8 fixes for Twitter Bootstrap
def render_conditional_comment_js(url, condition = 'lt', version = '9'):
    return '<!--[if %s IE %s]>%s<![endif]-->' % (condition, version, render_js(url))
html5shiv_js = Resource(library, "html5shiv.min.js", renderer = render_conditional_comment_js)

def includeme(config):
    #WARNING! deform_autoneed will change, so this code will be removed later on.

    #Replace bootstrap css
    bootstrap_css_path = 'deform:static/css/bootstrap.min.css'
    if resource_registry.find_resource(bootstrap_css_path):
        resource_registry.replace_resource(bootstrap_css_path, bootstrap_css)
    #Replace jquery
    jquery_path = 'deform:static/scripts/jquery-2.0.3.min.js'
    if resource_registry.find_resource(jquery_path):
        resource_registry.replace_resource(jquery_path, jquery)
    #Replace bootstrap js
    bootstrap_js_path = 'deform:static/scripts/bootstrap.min.js'
    if resource_registry.find_resource(bootstrap_js_path):
        resource_registry.replace_resource(bootstrap_js_path, bootstrap_js)
