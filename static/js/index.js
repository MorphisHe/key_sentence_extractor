var dragging = false;
$("#dragbar").mousedown(function (e) {
  e.preventDefault();
  dragging = true;

  $(document).mousemove(function (e) {
    if (dragging) {
      var percentage = (e.pageX / window.innerWidth) * 100;
      var contLeftPercentage = 100 - percentage;

      
      $("#pdf-container").css("width", "0%");
      $("#container-left").css("width", percentage + "%");
      $("#container-right").css("width", contLeftPercentage + "%");
    }
  });
});

$(document).mouseup(function (e) {
  dragging = false;
  $("#pdf-container").css("width", "100%");
  document.getElementById("pdf-container").page = 1;
});
