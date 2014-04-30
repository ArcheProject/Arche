

def includeme(config):
    config.include('arche.views.actions')
    config.include('arche.views.auth')
    config.include('arche.views.base')
    config.include('arche.views.contents')
    config.include('arche.views.file')
    config.include('arche.views.groups')
    config.include('arche.views.listing')
    config.include('arche.views.initial_setup')
    config.include('arche.views.image')
    config.include('arche.views.permissions')
    config.include('arche.views.portlets')
    config.include('arche.views.selected_content')
    config.include('arche.views.search')
    config.include('arche.views.system')
    config.include('arche.views.view_settings')
    config.include('arche.views.users')
