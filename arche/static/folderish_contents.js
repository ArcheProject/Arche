/* Handle loading and sorting of folderish contents.
   This will need to be generalised more if it's to be made reusable.
*/

var content_table_tpl;

function update_table_from_response(response) {
    if (typeof(content_table_tpl) === 'undefined') {
        content_table_tpl = $("#sortable").clone().html();
    } else {
        $("#sortable").html(content_table_tpl);
    }
    var directive = {'tr':
        {'obj<-items':
            {
                '.title': 'obj.title',
                '.title@class+': function(arg) {
                    if (arg.item['workflow'] != '') {
                        return ' workflow-' + arg.item['workflow'] + ' wf-state wf-state-' + arg.item['wf_state'];
                    }
                    return '';
                },
                'input[name="select"]@value': 'obj.__name__',
                'input[name="content_name"]@value': 'obj.__name__',
                'a@title': 'obj.description',
                '.type_title': 'obj.type_title',
                '.mimetype': 'obj.mimetype',
                '.created': 'obj.created',
                '.modified': 'obj.modified',
                '.tags': 'obj.tags',
                '.size': 'obj.size',
                '[data-css-icon]@class': 'obj.css_icon',
                'a@href': function(arg) {
                    var out = './' + arg.item['__name__']
                    if (arg.item['is_folder']) {
                        out += '/contents';
                    }
                    return out
                }
            }
        }
    };
    $("#sortable [data-load-msg]").remove();
    $('#sortable').render(response, directive);

    $('#sortable').sortable({
        handle: ".sortable-drag"
    }).disableSelection();

    $("#sortable").on("sortupdate", function(event, ei) {
        var form = $(event.currentTarget).parents('form');
        var url = form.attr('action');
        form.find('[name="action"]').attr('value', 'sort');
        var request = arche.do_request(url, {data: form.serialize(), method: 'post'});
        request.fail(arche.flash_error);
        form.find('[name="action"]').attr('value', '');
    });
}


$(function () {
    var request = arche.do_request('./contents.json');
    request.done(update_table_from_response);

    $('[data-delete-button]').on('click', function(event) {
        var form = $('#contents-form');
        event.preventDefault();
        form.find('[name="action"]').attr('value', 'delete');
        var url = form.attr('action');
        var data = form.serialize();
        var request = arche.do_request(url, {data: data, method: 'post'});
        request.done(update_table_from_response);
        form.find('[name="action"]').attr('value', '');
    });

    $('#fileupload').fileupload({
        dataType: 'json',
        done: function (e, response) {
            update_table_from_response(response.result);
        },
        error: function(response) {
            arche.flash_error(response);
        }
    });
});
