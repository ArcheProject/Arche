//Global namespace for global variables and functions. Be careful.
arche = {};
arche.flash_slot_order = ['modal', 'main'];
arche.default_flash_timer = 3000;
arche.online_status = true;

// Disable cache functionality. To enable this we need proper cache headers on responses
$.ajaxSetup ({
  cache: false
});

function do_request(url, options) {
    var settings = {url: url, async: true, timeout: 30000};
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
 * 
 * params
 *   - modal-class: class(es) to use on the modal-dialog element. Defaults to ''.
 *     use this to set size.
 */
function create_modal(url, params) {
  if (typeof(params) == 'undefined') var params = {};
  var modal_dialog_cls = typeof params['modal-dialog-class'] !== 'undefined' ? params['modal-dialog-class'] : '';
  arche.destroy_modal();
  var out = '<div class="modal fade" id="modal-area" tabindex="-1" role="dialog" aria-labelledby="modal-title" aria-hidden="true">';
  out += '<div class="modal-dialog ' + modal_dialog_cls + '"><div class="modal-content"></div></div></div>';
  var request = arche.do_request(url, {data: {modal: 1}});
  request.done(function(response) {
    $('body').prepend(out);
    $('.modal-content').append(response);
    //Inject modal flash slot if it doesn't exist
    if ($('[data-flash-slot="modal"]').length == 0) {
      if ($('.modal-body:first').length == 1) {
        $('.modal-body:first').prepend('<div data-flash-slot="modal"></div>');
      } else {
        $('.modal-content').prepend('<div data-flash-slot="modal"></div>');
      }
    }
    $('#modal-area').modal();
    $('#modal-area').one('hidden.bs.modal', arche.destroy_modal);

  });
  request.fail(function(jqXHR) {
    arche.flash_error(jqXHR);
  })
  return request;
}
arche.create_modal = create_modal;

function destroy_modal() {
  $('body').removeClass('modal-open');
  $('.modal-backdrop').remove();
  $('.modal').remove();
}
arche.destroy_modal = destroy_modal;


/* Create a modal window when an element is clicked
 * ================================================
 * Example =
 *  <a href="<somewhere>" data-open-modal>I'm modal</a>
 *  If data-modal-dialog-class is set, add those classes to the modal window.
 *  Defaults to 'fade'. "modal' will always be included.
 *  Will open a modal window with the content of <somewhere>
 */
function modal_from_event(event) {
  event.preventDefault();
  var elem = $(event.currentTarget);
  if (elem.data('opening') == true) return;
  elem.data('opening', true);
  if (typeof elem.attr('data-url') == 'undefined') {
    var url = elem.attr('href');
  } else {
    var url = elem.data('url');
  }
  var params = {};
  params['modal-dialog-class'] = elem.data('modal-dialog-class');
  if (typeof(url) == 'undefined') {
    throw "couldn't find any href or data-url attribute to load a modal window from on " + elem;
  }
  arche.actionmarker_feedback(elem, true);
  var request = arche.create_modal(url, params);
  request.always(function() {
    arche.actionmarker_feedback(elem, false);
    elem.removeData('opening');
  });
}
arche.modal_from_event = modal_from_event;


/* Create a flash message and display it
 * =====================================
 * Message will be inserted in an element that has the marker data-flash-slot="<something>",
 * where <something> should be values from arche.flash_slot_order.
 * The point of this is to make sure flash messages are displayed in a visible area.
 * 
 * Note that any flash messages added with the python adapter IFlashMessages
 * will be loaded and displayed by this function.
 * 
 * params:
 *  - type: which alert type this is. See twitter bootstrap alerts
 *  - id: in case you want to set it in advance to reference it in some way.
 *  - slot: render in this slot, otherwise use the first available.
 *  - auto_destruct: If set and the message isn't of the type 'danger', remove message
 *    automatically after any number of miliseconds specified at arche.default_flash_timer
 */

function create_flash_message(message, params) {
  params = typeof params !== 'undefined' ? params : {};
  params['type'] = typeof params['type'] !== 'undefined' ? params['type'] : 'info';
  params['id'] = typeof params['id'] !== 'undefined' ? params['id'] : "msg-" + Math.round(Math.random()* 10000000);
  if (params['type'] == 'danger' && typeof params['auto_destruct'] == 'undefined') {
    params['auto_destruct'] = false;
  }
  params['auto_destruct'] = typeof params['auto_destruct'] !== 'undefined' ? params['auto_destruct'] : true;

  var target;
  // Specific slot specified?
  if (typeof params['slot'] !== 'undefined') {
    if ($('[data-flash-slot="' + params['slot'] + '"]').length > 0) {
      target = $('[data-flash-slot="' + params['slot'] + '"]');
    }
    if (typeof(target) == 'undefined') throw "Flash slot doesn't exist: " + params['slot'];
  // Use first available
  } else {
    $.each(arche.flash_slot_order, function( index, value ) {
      if ($('[data-flash-slot="' + value + '"]').length > 0) {
        target = $('[data-flash-slot="' + value + '"]');
        return false;
      }
    });
    if (typeof(target) == 'undefined') throw "No flash-slot found, tried: " + arche.flash_slot_order;
  }

  var out = '<div role="alert" id="' + params['id'] + '" class="alert alert-dismissable alert-'+ params['type'] + '">';
  out += '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>';
  if (params['icon_class']) {
    out += '<span class="' + params['icon_class'] +'"></span>&nbsp;&nbsp;&nbsp;';
  }
  out += '<span class="msg-part">' + message + '</span>';
  out += '</div>';

  if (params['auto_destruct'] === true) {
    //FIXME: Create smarter timeouts here. Pop one message at a time for instance.
    setTimeout( function() { $('#' + params['id']).slideUp(400, function() {this.remove()}); }, arche.default_flash_timer );
  }
  $('[data-flash-slot] .msg-part').each(function(index) {
    if ($(this).text() == message) {
        $(this).parents('[role="alert"]').remove();
    }
  })
  target.append(out);
  $('#' + params['id']).hide().slideDown();
};
arche.create_flash_message = create_flash_message;


/* Load flash messages from session storage
 * ========================================
 * If json response isn't provided as argument,
 * this function will simply load them from the standard url.
 */
function load_flash_messages(response) {
  if (typeof(response) === 'undefined') {
    var request = arche.do_request('/flash_messages.json')
    request.done(load_flash_messages);
  } else {
    $.each(response, function(index, value) {
      arche.create_flash_message(value[0], value[1])
    });
  };
};
arche.load_flash_messages = load_flash_messages;


//Attach this to .fail on deferred objects
function flash_error(jqXHR) {
  //Connection problems will have a status == 0 and no text so this function should be updated.
  if (jqXHR.status == 0) {
    if ($('#connection-warning').length == 0) {
        //FIXME: Translation
        switch(jqXHR.statusText) {
            case 'timeout':
                var msg = "Timeout"
                break;
            default:
                if (arche.online_status) {
                    var msg = "Connection error";
                } else {
                    var msg = "Conenction error - you seem to be offline"
                }
        }

        arche.create_flash_message(msg, {type: 'warning', id: 'connection-warning'});
    }
  } else {
      arche.create_flash_message('<h4>' + jqXHR.status + ' ' + jqXHR.statusText + '</h4>' + jqXHR.responseText,
          {type: 'danger', auto_destruct: true});
  }
}
arche.flash_error = flash_error;

/* Things performing ajax actions can have this function showing status for them.
 * Add an element within the structure you pass to it. Example:
 * <span data-actionmarker="glyphicon glyphicon-refresh rotate-me"></span>
 * 
 * The data-actionmarker values will be added as classes to the span
 */
arche.actionmarker_feedback = function(elem, active) {
  var elem = $(elem);
  var elems = $(elem).find('[data-actionmarker]');
  if (elem.data('actionmarker')) elems.push(elem);
  $.each(elems, function() {
    if (active == true) {
      $(this).addClass($(this).data('actionmarker'));
    } else {
      $(this).removeClass($(this).data('actionmarker'));
    }
  })
}

/* Function to handle multi-select.
   On the trigger: data-mselect-for="<name>"
   On the items that should be triggered: data-mselect-name="<name>"
 */
arche.multi_select = function(event) {
    var name = $(event.currentTarget).data('mselect-for');
    var target_selectors = $('[data-mselect-name="' + name + '"]');
    target_selectors.prop("checked", $(event.currentTarget).prop("checked"));
}

$(document).ready(function() {
  // Modal window listener for links with href defined
  $('body').on('click', "[data-open-modal]", arche.modal_from_event);
  $('body').on('click', '[data-mselect-for]', arche.multi_select)
  arche.load_flash_messages();
});


window.addEventListener('offline', function(event) {
    arche.online_status = false;
});


window.addEventListener('online', function(event) {
    arche.online_status = true;
});
