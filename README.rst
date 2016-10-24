Arche README
============

Arche development version


Paster ini settings
===================

arche.hash_method (default: 'arche.security.sha512_hash_method')
  Method used to encrypt password. Must accept value as positional argument and and hashed as a keyword.


arche.session_factory (default: 'pyramid_beaker')
  Pyramid session factory. Also works with pyramid_redis_sessions or others.


arche.includes (default: '')
  Any arche plugins to load. These load after arche. If you need them to load before, use pyramid.includes instead.


arche.debug (default: false)
  Show debug messages.


arche.use_exception_views (default: true)
  Load the special views ment for exceptions.


arche.timezone (default: 'UTC')
  Default timezone. (Like 'Europe/Stockholm')


arche.cache_max_age (default: 24*60*60)
  Default cache value for resources, specified in seconds.


arche.new_userid_validator (default: 'arche.validators.NewUserIDValidator')
  See the validator on how to override it.


arche.actionbar (default: 'arche.views.actions.render_actionbar')
  What to render as the actionbar. It may be disabled here too.


arche.auto_recreate_catalog (default: false)
  Rebuild and reindex catalog whenever it's needed.
  You may use this setting on production servers if:
  1. You only have one instance. (If you rebuild 2 at once you'll get commit error on the second one)
  2. You're aware that rebuilding the catalog may take a long time!


arche.favicon (default: '')
  Path to favicon, including package.
  Example: 'arche:static/favicon.ico'


arche.authn_factory (default: 'arche.security.auth_tkt_factory')
  Pyramid Authentication factory. The auth_tkt_factory adds a factory creating
  encrypted cookies with auth information. You may use auth_session_factory
  to store data in the session instead. 
  
  
arche.auth.max_sessions (default: 5)
  If any mechanism to keep track of active auth sessions is used, specify max number of active here.
  Relevant for 'arche.plugins.auth_sessions'.


arche.auth.activity_update (default: 60)
  Track activity every X seconds. Relevant for 'arche.plugins.auth_sessions'.


arche.auth.default_max_valid (default: 60)
  How many minutes should an authentication session be valid?
  Relevant for 'arche.plugins.auth_sessions' but may also affect other things.
  If this is set to 0, sessions will never expire. Don't do this.


arche.auth.max_keep_days (default: 30)
  Keep activity logs for this amount of days. Relevant for 'arche.plugins.auth_sessions'.
