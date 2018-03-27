'use strict';

/*
See templates/master.pt for example structure of livesearch.
The #search form implements it.
*/

function SearchWatcher (search_selector) {
    this.search_selector = search_selector;
    this.tpl = null;
    this.directive = {
        'li':{
            'obj<-results':{
                '[data-title]': 'obj.title',
                '[data-css-icon]@class+': 'obj.css_icon',
                'a@href': 'obj.url',
                'a@class+': function(a) {
                    return " " + a.item.type_name;
                },
                '[data-img]@src': 'obj.thumb_url',
            }
        }
    }
    this.delay_time = 1000;
    this.hide_delay = 3000;
    this.min_chars = 2;
    this.timer = null;
    this.timer_hide = null;
    this.has_results = false;

    this.search = function(search_field) {
        var form = search_field.parents('form')
        if (form.length == 1) {
            arche.actionmarker_feedback(form, true);
            var url = form.data('watch-url');
            if (!url) url = form.attr('action');
            var request = arche.do_request(url, {data: form.serialize(), method: form.attr('method')});
            request.done(this.handle_search_response.bind(this));
            request.always(function() {
                arche.actionmarker_feedback(form, false);
            });
        }
    }

    this.handle_change_event = function(event) {
        if (this.timer != null) {
            clearTimeout(this.timer);
        }
        var target = $(this.target_name);
        if (!target.hasClass('active')) target.removeClass('active');
        var search_field = $(event.currentTarget);
        if (search_field.val().length >= this.min_chars) {
            this.timer = setTimeout(
                function() { this.search(search_field) }.bind(this), this.delay_time);
        }
    }

    this.handle_search_response = function(response) {
        if (this.timer_hide != null) {
            clearTimeout(this.timer_hide);
        }
        if (!this.tpl) this.tpl = $(this.target_name).html();
        $(this.target_name).html(this.tpl);
        if (response.results.length > 0) {
            this.has_results = true;
            $(this.target_name).render(response, this.directive);
        } else {
            this.has_results = false;
        }
        var msg_elem = $(this.target_name).children('[data-search-msg]');
        if (response.msg) {
            msg_elem.html(response.msg);
        } else {
            msg_elem.html("");
        }
        $(this.target_name).addClass('active');
        //this.start_close_timer();
    }

    this.handle_mouseon = function(event) {
        if (this.timer_hide != null) {
            clearTimeout(this.timer_hide);
        }
    }

    this.handle_mouseleave = function(event) {
        this.start_close_timer();
    }

    this.handle_mouseon_reopen = function(event) {
        if (this.has_results) $(this.target_name).addClass('active');
    }

    this.start_close_timer = function() {
        if (this.timer_hide != null) {
            clearTimeout(this.timer_hide);
        }
        this.timer_hide = setTimeout( function() {
            $(this.target_name).removeClass('active');
        }.bind(this), this.hide_delay);
    }

    $('body').on('input propertychange', this.search_selector, this.handle_change_event.bind(this));
    this.target_name = $(this.search_selector).data('watch-search');
    $('body').on('mouseleave', this.target_name, this.handle_mouseleave.bind(this));
    $('body').on('mouseover', this.target_name, this.handle_mouseon.bind(this));
    $('body').on('mouseleave', this.search_selector, this.handle_mouseleave.bind(this));
    $('body').on('mouseover', this.search_selector, this.handle_mouseon_reopen.bind(this));
}

SearchWatcher.handle_close_results = function(event) {
    event.preventDefault();
    var target = $(event.currentTarget).data('close-results');
    $(target).removeClass('active');
}



$(document).ready(function() {
    $('body').on('click', '[data-close-results]', SearchWatcher.handle_close_results);
    $.each($('[data-watch-search]'), function(index, elem) {
        if (elem.id) {
            $(elem).data('searchwatcher', new SearchWatcher('#' + elem.id));
        }
    });
});
