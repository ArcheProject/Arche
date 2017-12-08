'use strict';

/*
<form
    action="${request.resource_url(request.root,'search')}"
    data-watch-url="${request.resource_url(request.root,'search.json')}"
    id="search">

<input
    id="example"
    data-watch-search="#popup-results">

<div id="popup-results">
    <p class="text-right"><a data-close-results="#popup-results" href="#">Close</a></p>
    <span data-no-results="No results"></span>
    <ul  class="list-unstyled">
        <li>
            <a class="text-overflow" href="">
                <span data-title></span>
                <span class="pull-right" data-img></span>
            </a>
        </li>
    </ul>
</div>
*/


class SearchWatcher {

    constructor(search_selector) {
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
        $('body').on('input propertychange', this.search_selector, this.handle_change_event.bind(this));
        this.target_name = $(this.search_selector).data('watch-search');
        $('body').on('mouseleave', this.target_name, this.handle_mouseleave.bind(this));
        $('body').on('mouseover', this.target_name, this.handle_mouseon.bind(this));
        $('body').on('mouseleave', this.search_selector, this.handle_mouseleave.bind(this));
        $('body').on('mouseover', this.search_selector, this.handle_mouseon_reopen.bind(this));
    }

    search(search_field) {
        console.log('will search');
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

    handle_change_event(event) {
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

    handle_search_response(response) {
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

            //var no_res_elem = $(this.target_name).children('[data-no-results]');
            //if (no_res_elem.length == 1) no_res_elem.html(no_res_elem.data('no-results'));
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

    handle_mouseon(event) {
        if (this.timer_hide != null) {
            clearTimeout(this.timer_hide);
        }
    }

    handle_mouseleave(event) {
        this.start_close_timer();
    }

    handle_mouseon_reopen(event) {
        if (this.has_results) $(this.target_name).addClass('active');
    }

    start_close_timer() {
        if (this.timer_hide != null) {
            clearTimeout(this.timer_hide);
        }
        this.timer_hide = setTimeout( function() {
            $(this.target_name).removeClass('active');
        }.bind(this), this.hide_delay);
    }

    static handle_close_results(event) {
        event.preventDefault();
        var target = $(event.currentTarget).data('close-results');
        $(target).removeClass('active');
    }
}


$(document).ready(function() {
    $('body').on('click', '[data-close-results]', SearchWatcher.handle_close_results);
    $.each($('[data-watch-search]'), function(index, elem) {
        if (elem.id) {
            $(elem).data('searchwatcher', new SearchWatcher('#' + elem.id));
        }
    });
});
