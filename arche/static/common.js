//Global namespace for global variables and functions. Be carefull.
arche = {};

function do_request(url, options) {
    var settings = {url: url, async: false};
    if (typeof(options) !== 'undefined') $.extend(settings, options);
    var request = $.ajax(settings);
    request.fail(function(jqXHR) {
        // So something with the fail like:
        console.log(jqXHR.status + ' ' + jqXHR.statusText);
    });
    return request;
}
arche.do_request = do_request;
