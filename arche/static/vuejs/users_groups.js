// TODO Move components to a separate file for generic use.

Vue.component('select2', {
  props: ['value', 'placeholder'],
  template: '<select><slot></slot></select>',
  mounted: function () {
    var vm = this
    var src = this.$el.dataset.src;
    if (src) {
      $(this.$el)
      // init select2
      .select2({
        minimumInputLength: 1,
        containerCssClass: 'form-control',
        width: "100%",
        placeholder: this.placeholder,
        ajax: {
          url: this.$el.dataset.src,
          dataType: 'json',
          delay: 250,
          data: function (params) {
            return {
              query: params.term, // search term
              page_limit: 10,
            };
          },
        }
      })
      .val(this.value)
      .trigger('change')
      // emit event on change.
      .on('change', function () {
        vm.$emit('input', this.value)
      })
    }
  },
  watch: {
    value: function (value) {
      // update value
      $(this.$el)
      	.val(value)
      	.trigger('change')
    },
  },
  destroyed: function () {
    $(this.$el).off().select2('destroy')
  }
})

$(function() {
    var user_app = new Vue({
      data: {
        users: [],
        userPages: {},
        itemsPerPage: 50,
        orderBy: "userid",
        orderReversed: false,
        query: ""
      },
      props: ['addUserSelected', 'currentPage', 'total'],
      el: "#user-table",
      mounted: function() {
        this.getPage(0);
      },
      methods: {
        clear: function() {
          this.users = [];
        },
        getRange: function(start) {
          var params = {
            start: start,
            limit: this.itemsPerPage,
            order: this.orderBy,
            q: this.query,
            reverse: this.orderReversed
          };
          return arche.do_request(this.$el.dataset.src, {data: params})
          .done(function(response) {
            for (i=0; i<response.items.length; i++) {
              this.users[start + i] = response.items[i];
            }
            this.total = response.total;
          }.bind(this));
        },
        getPage: function(page) {
          if (typeof page === 'undefined') page = 0;
          var start = page*this.itemsPerPage;
          if (this.users[start]) {
            this.currentPage = page;
          } else {
            this.currentPage = undefined;
            this.getRange(start)
            .done(function() {
              this.currentPage = page;
            }.bind(this));
          }
        },
        search: function() {
          this.clear();
          this.getPage();
        },
        searchTimer: function() {
          if (this.timer) {
            clearTimeout(this.timer);
          }
          this.timer = setTimeout(this.search.bind(this), 200);  // 200 ms
        },
        setOrder: function(value) {
          this.orderBy = value;
          this.search();
        },
        reverseOrder: function() {
          this.orderReversed = !this.orderReversed;
          this.search();
        },
        userApi: function(api, userID) {
          do_request(api, {
            method: 'POST',
            data: {userid: userID}
          })
          .done(function() {
            this.search();
          }.bind(this))
          .fail(function(xhr) {
            arche.create_flash_message(
                xhr.responseText,
                {type: 'danger', auto_destruct: true}
            );
          })
        },
        addUser: function() {
          var target = $(event.target).closest('[data-target]').data('target');
          var userID = this.addUserSelected;
          if (!userID) return;
          this.userApi(target, userID);
        },
        removeUser: function(userID) {
          var target = $(event.target).closest('[data-target]').data('target');
          this.userApi(target, userID);
        }
      },
      computed: {
        currentUsers: function() {
          var start = this.currentPage * this.itemsPerPage;
          return this.users.slice(start, start + this.itemsPerPage);
        },
        pages: function() {
          var pages = [];
          var endPage = Math.floor(this.total / this.itemsPerPage);
          var sliceStart = this.currentPage - 3;
          var sliceEnd = this.currentPage + 3;
          if (sliceStart < 0 !== sliceEnd > endPage) {  // Only one is off
            if (sliceStart < 0) {  // Start is off
              sliceEnd = 6;
            } else {  // End is off
              sliceStart = endPage - 6;
            }
          }
          // Make sure nothing is off after this.
          sliceStart = Math.max(sliceStart, 0);
          sliceEnd = Math.min(sliceEnd, endPage);
          if (typeof this.total !== 'undefined') {
            if (sliceStart > 0) {
              pages.push({
                text: '«',
                id: 0
              });
            }
            for (page=sliceStart; page<=sliceEnd; page++) {
              var start = (page * this.itemsPerPage) + 1;
              var end = Math.min((page * this.itemsPerPage) + this.itemsPerPage, this.total);
              pages.push({
                text: (start === end) ? start : start + ' - ' + end,
                active: page === this.currentPage,
                id: page
              });
            }
            if (sliceEnd < endPage) {
              pages.push({
                text: '»',
                id: endPage
              });
            }
          }
          return pages;
        }
      },
      watch: {
        query: function(val) {
          this.searchTimer();
        }
      }
    });
})
