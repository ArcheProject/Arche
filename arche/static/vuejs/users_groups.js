// TODO Move components to a separate file for generic use.

Vue.component('select2', {
  props: ['value'],
  template: '<select><slot></slot></select>',
  mounted: function () {
    var vm = this
    $(this.$el)
      // init select2
      .select2({
        minimumInputLength: 1,
        containerCssClass: 'form-control',
        width: "100%",
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
        itemsPerPage: 100,
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
          this.itemsPerPage=100;
        },
        setTotal: function(total) {
          var perPage = 20;
          if (total >= 200) perPage = 50;
          if (total >= 1000) perPage = 100;
          this.itemsPerPage = perPage;
          this.total = total;
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
            this.setTotal(response.total);
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
        addRemove: function(target, userID) {
          do_request(target, {
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
        addUser: function(event) {
          var target = event.target.dataset.target;
          var userID = this.addUserSelected;
          if (!userID) return;
          this.addRemove(target, userID);
        },
        removeUser: function(userID) {
          var target = event.target.dataset.target;
          this.addRemove(target, userID);
        }
      },
      computed: {
        currentUsers: function() {
          var start = this.currentPage * this.itemsPerPage;
          return this.users.slice(start, start + this.itemsPerPage);
        },
        pages: function() {
          var pages = [];
          var slicePages = [];
          var endPage = Math.floor(this.total / this.itemsPerPage);
          var sliceStart = Math.max(0, this.currentPage - 3);
          var sliceEnd = Math.min(endPage, this.currentPage + 3);
          if (typeof this.total !== 'undefined') {
            var count = Math.ceil(this.total / this.itemsPerPage);
            for (page=0; page<count; page++) {
              var start = (page * this.itemsPerPage) + 1;
              var end = Math.min((page * this.itemsPerPage) + this.itemsPerPage, this.total);
              slicePages.push({
                text: start + ' - ' + end,
                active: page === this.currentPage,
                id: page
              });
            }
            if (sliceStart > 0) {
              pages.push({
                text: '«',
                id: 0
              });
            }
            pages = pages.concat(slicePages.slice(sliceStart, sliceEnd + 1));
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
