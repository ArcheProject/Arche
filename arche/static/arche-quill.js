ArcheQuill = function(oid, options) {
    this.$storage = $(oid).siblings('.arche-ql-storage');
    this.editor = new Quill(oid, options);
    this.editor.on('text-change', this.textChange.bind(this));
}
ArcheQuill.prototype.textChange = function() {
    this.$storage.html(this.editor.root.innerHTML);
}

function createArcheQuill(oid, options) {
    deform.addCallback(oid, function() {
        new ArcheQuill(oid, options);
    });
}


(function($){
    var ImageFormat = Quill.import('formats/image');
    class CustomImage extends ImageFormat {
//      https://github.com/quilljs/quill/blob/develop/formats/image.js
    }
    CustomImage.blotName = 'custom';
    CustomImage.className = 'arche-image';
    Quill.register(CustomImage);
})(jQuery);
