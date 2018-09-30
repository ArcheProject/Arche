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


Optional settings
-----------------

arche.versioning.<TypeName> = <attribute> <..>
  Switch on versioning for a specific type. Attributes to store needs to be specified.

  Example, add versioning for 'body' and 'description' for any 'Document':

  arche.versioning.Document = body description


arche.workflows = <TypeName> <WorkflowName>
  Set workflow.
  Example: Document simple_workflow


Config directives
=================

config.add_script(<callable>, name=None, **kw)
  Add a script executable with the arche-command.
  Callable is the script, which must accept bootstrap 'env' dict and the
  result of argparse as another positional argument.

  See arche.scrips for examples


config.add_workflow(<workflow class>)
  Register a workflow.


config.set_content_workflow(<type_name: str>, <wf_name: str>)
  Set a content type to a specific workflow. Workflow name should be the same as the
  'name'-attribute on the workflow class.


config.register_roles(<Role instance>, ...)
  Register one or many roles so it's possible to assign permissions to them.


config.add_portlet(<portlet>)
  Add a PorletType class as an addable portlet.


config.add_portlet_slot(name, title = "", layout = "")
  Create a slot where portlets can be assigned. Layout is an optional keyword.
  Currently we use 'horizontal' and 'vertical' in Arche.


config.add_versioning(<iface_or_ctype>, attributes = ())
  Enable versioning for something that has either the specific type_name,
  or implements an interface. Attribute(s) must be specified too. Whenever
  the value changes, the new value is stored along with a timestamp and the person who changed it.


config.add_content_factory(<ctype>, addable_to = (), addable_in = ())
  Add content factory. (I.e. a class for a resource)

  addable_to: Where this content is addable. (List or string)

  addable_in: Other content that's addable within this. (List or string)


config.add_addable_content(ctype, addable_to)
  Set that a type is addable within another type within the resource tree.
  (I.e. shows up in the add menu)


config.add_schema(<type_name: str>, <schema>, <names>)
  Add a schema to the schema registry. Schemas have a type name association and a
  function name.
  Usually something like:

  config.add_schema('Page', PageSchema, 'edit')


config.add_content_view(type_name, name, view_cls)
  Add a selectable view for a specific content type. The view class must implement IContentView.

  Example: config.add_content_view('Blog', 'chronological_order', ChronologicalOrderView)
