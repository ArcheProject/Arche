
$(document).ready(function() {
  
  $( ".portlet-sortable" ).sortable({
    //connectWith: ".portlet-sortable",
    handle: ".sortable-drag"
  }).disableSelection();

  $(".portlet-sortable").on("sortupdate", function(event, ei) {
    var url = $(event.currentTarget).data('portlet-saveurl');
    var uids = [];
    $(event.currentTarget).children().each(function(i, val) {
      uids.push($(val).data('uid'));
    });
    request = arche.do_request(url, {data: {'uids': uids}, method: 'POST'});
    request.fail(arche.flash_error);
  });
});
