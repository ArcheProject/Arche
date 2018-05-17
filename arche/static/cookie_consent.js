"use strict";

function handleCookieConsent(event) {
    $('#cookie-consent-container').hide();
    window.localStorage.cookieConsent = true;
}

$(function() {
    if (window.localStorage && !window.localStorage.cookieConsent) {
        arche.do_request('/__cookie_consent__')
        .done(function(data) {
            var $content = $(data.trim());
            $content.find('button.cookie-close').click(handleCookieConsent);
            $('body').append($content);
        });
    }
});
