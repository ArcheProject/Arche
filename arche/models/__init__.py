def includeme(config):
    """ Load all models"""
    config.include('.blob')
    config.include('.catalog')
    config.include('.datetime_handler')
    config.include('.file_upload')
    config.include('.flash_messages')
    config.include('.jsondata')
    config.include('.mimetype_views')
    config.include('.roles')
    config.include('.thumbnails')
    config.include('.workflow')
