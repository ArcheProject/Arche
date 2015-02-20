//Global namespace for global variables and functions. Be carefull.
arche = {};

function do_request(url, options) {
    var settings = {url: url, async: true};
    if (typeof(options) !== 'undefined') $.extend(settings, options);
    var request = $.ajax(settings);
    request.fail(function(jqXHR) {
        // So something with the fail like:
        console.log(jqXHR.status + ' ' + jqXHR.statusText);
    });
    return request;
}
arche.do_request = do_request;

/* Extracts error messages from a json response.
 * - Only works on pages with a single form right now. (Fix this!)
 * - form-control and form-group classes must be present. (See twitter bootstrap docs)
 * - Each form element must have a unique name
 */
function handle_form_errors(response) {
  $('.has-error .form-control').tooltip('destroy');
  $('.has-error').each(function() {
    $(this).removeClass('has-error');
  });
  if (!('errors' in response)) {
    return;
  }
  for (var key in response['errors']) {
    var form_elem = $('.form-control[name="' + key + '"]');
    //form_elem.before( msg );
    form_elem.parents('.form-group').addClass('has-error');
    form_elem.tooltip({title: response['errors'][key], placement: 'top'});
    form_elem.tooltip('show');
  }
}
arche.handle_form_errors = handle_form_errors;

/* Handle modal content
 * - data-modal-target must be set on selector_id
 * */

function create_modal(selector_id) {
  $('.modal').remove();
  var btn = $(selector_id);
  var url = btn.data('modal-target');
  var request = arche.do_request(url);
  request.done(function(response) {
    $('body').prepend(response);
    $(selector_id + '-modal').modal();
    //Is this valid on all occations?
    deform.processCallbacks();
    deform.focusFirstInput();
  });
}
arche.create_modal = create_modal;

function destroy_modal() {
  $('body').removeClass('modal-open');
  $('.modal-backdrop').remove();
  $('.modal').remove();
}
arche.destroy_modal = destroy_modal;


/* Create and pop flash message
 * parmas are the same as the flash_messages view
 */

function create_flash_message(message, params) {
  if (typeof(params) === 'undefined') var params = {};
  params['message'] = message;
  var request = arche.do_request('/__flash_messages__', {type: "POST", data: params})
  request.done(arche.load_flash_messages);
};
arche.create_flash_message = create_flash_message;

function load_flash_messages(response) {
  if (typeof(response) === 'undefined') {
    var request = arche.do_request('/__flash_messages__')
    request.done(load_flash_messages);
  } else {
    var target = $('#messages');
    if (!target.length > 0) target = $('body > .container:first'); //Fallback
    target.prepend(response);
  };
};
arche.load_flash_messages = load_flash_messages;
