def includeme(config):
    """ Load all models"""
    config.include('.blob')
    config.include('.catalog')
    config.include('.datetime_handler')
    config.include('.evolver')
    config.include('.file_upload')
    config.include('.flash_messages')
    config.include('.folder')
    config.include('.jsondata')
    config.include('.mimetype_views')
    config.include('.reference_guard')
    config.include('.versioning')
    config.include('.workflow')
