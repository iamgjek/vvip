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


    $(document).ready(function() {
       $('#bs1').multiselect({
           enableHTML: true,
                             nonSelectedText: '權屬',
                             buttonWidth: '170px',
                             numberDisplayed: 6
         });
     });


     $(document).ready(function() {
        $('#enable').multiselect({
            nonSelectedText: '登記原因',
            buttonWidth: '170px',
            numberDisplayed: 6
          });
      });


      $(document).ready(function() {
         $('#bs3').multiselect({
                               nonSelectedText: '國土區分',
                               numberDisplayed: 6,
             buttonWidth: '170px',
           });
       });

       $(document).ready(function() {
          $('#example-getting-started').multiselect({
              enableHTML: true,
                                 nonSelectedText: '國籍',
               buttonWidth: '170px',
            });
        });
