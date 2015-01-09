def includeme(config):
    """ Load all models"""
    config.include('.blob')
    config.include('.datetime_handler')
    config.include('.file_upload')
    config.include('.flash_messages')
    config.include('.jsondata')
