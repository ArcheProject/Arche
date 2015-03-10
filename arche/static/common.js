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
 */
function create_modal(url) {
  arche.destroy_modal();
  var out = '<div class="modal fade" id="modal-area" tabindex="-1" role="dialog" aria-labelledby="modal-title" aria-hidden="true">';
  out += '<div class="modal-dialog"><div class="modal-content"></div></div></div>';
  $('body').prepend(out);
  var request = arche.do_request(url);
  request.done(function(response) {
    $('.modal-content').html(response);
    $('#modal-area').modal();
  });
  request.fail(function(jqXHR) {
    arche.flash_error(jqXHR);
    arche.destroy_modal();
  })
}
arche.create_modal = create_modal;

function destroy_modal() {
  $('body').removeClass('modal-open');
  $('.modal-backdrop').remove();
  $('.modal').remove();
}
arche.destroy_modal = destroy_modal;

function modal_from_event(event) {
  event.preventDefault();
  var elem = $(event.currentTarget);
  var url = elem.attr('href');
  if (typeof(url) == 'undefined') {
    throw "couldn't find any href attribute to load a modal window from on " + elem;
  }
  arche.create_modal(url);
}
arche.modal_from_event = modal_from_event;


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

/* Inject or load flash messages. If response isn't provided,
 * this function will simply load them.
 */
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

//Attach this to .fail on deferred objects
function flash_error(jqXHR) {
  arche.create_flash_message(jqXHR.status + ' ' + jqXHR.statusText, {type: 'danger'});
}
arche.flash_error = flash_error;

$(document).ready(function() {
  // Modal window listener for links with href defined
  $('body').on('click', "[data-open-modal]", function(event) {
    arche.modal_from_event(event);
  });
});
