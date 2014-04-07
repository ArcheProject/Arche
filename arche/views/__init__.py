

def includeme(config):
    config.include('arche.views.auth')
    config.include('arche.views.base')
    config.include('arche.views.listing')
    config.include('arche.views.initial_setup')
    config.include('arche.views.users')
