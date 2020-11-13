// col-dragger handler
var col_dragging = false;
$("#col-dragbar").mousedown(function (e) {
  e.preventDefault();
  col_dragging = true;

  $(document).mousemove(function (e) {
    if (col_dragging) {
      var percentage = (e.pageX / window.innerWidth) * 100;
      var contLeftPercentage = 100 - percentage;

      $("#pdf-container").css("width", "0%");
      $("#container-left").css("width", percentage + "%");
      $("#container-right").css("width", contLeftPercentage + "%");
    }
  });
});

// row-dragger handler
var row_dragging = false;
$("#row-dragbar").mousedown(function (e) {
    e.preventDefault();
    row_dragging = true;
  
    $(document).mousemove(function (e) {
      if (row_dragging) {
        var percentage = (e.pageY / window.innerHeight) * 100;
        var contBtmPercentage = 100 - percentage;
  
        $("#ckp-list").css("height", percentage + "%");
        $("#embedding-plot").css("height", contBtmPercentage + "%");
      }
    });
  });

// mouseup handler for dragging
$(document).mouseup(function (e) {
  if (col_dragging) {
    col_dragging = false;
    $("#pdf-container").css("width", "100%");
  }
  else if (row_dragging) {
      row_dragging = false;
  }
});
