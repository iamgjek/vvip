$(function () {
  $("[data-submenu]").submenupicker();
  $(".dropdown-toggle").on("click", function () {
    $(this).toggleClass("on");
  });

  $(".dropdown").on("hide.bs.dropdown", function () {
    $(".dropdown-toggle").removeClass("on");
  });

  $(document).on("keypress", "input", function (e) {
    var code = e.keyCode || e.which;
    if (code == 27) {
      $(".dropdown-toggle").removeClass("on");
    }
  });
});

  $(function(){
    $("#password1").peeper({
        mask: false,
        showPasswordCss: 'fa fa-eye',
        showCopyBtn: false
      });
  });