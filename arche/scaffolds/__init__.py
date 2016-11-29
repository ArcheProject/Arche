from pyramid.scaffolds import PyramidTemplate


class BuildoutTemplate(PyramidTemplate):
    _template_dir = 'buildout_template'
    summary = 'Basic buildout and design starter package'


class PluginTemplate(PyramidTemplate):
    _template_dir = 'plugin_template'
    summary = 'Package expected to be an Arche plugin'
