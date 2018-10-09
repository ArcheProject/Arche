$(function() {
    var user_app = new Vue({
      data: {
        users: [],
        userPages: {},
        currentPage: undefined,
        total: undefined,
        itemsPerPage: 100,
        orderBy: "userid",
        orderReversed: false,
        query: ""
      },
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
