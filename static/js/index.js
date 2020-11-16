// ========================== Dragbars ==========================
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
  } else if (row_dragging) {
    row_dragging = false;
  }
});



// ========================== DropBox ==========================
var drop = $("input");
drop
  .on("dragenter", function (e) {
    $(".drop").css({
      border: "4px dashed #09f",
      background: "rgba(0, 153, 255, .05)",
    });
    $(".cont").css({
      color: "#09f",
    });
  })
  .on("dragleave dragend mouseout drop", function (e) {
    $(".drop").css({
      border: "3px dashed #DADFE3",
      background: "transparent",
    });
    $(".cont").css({
      color: "#8E99A5",
    });
  });
  
function handleFileSelect(e) {
  // replace dropbox with pdf
  let filename = e.target.files[0].name;


  /** 
  var file = e.target.files[0];

  // Read the file using file reader
  var fileReader = new FileReader();

  fileReader.onload = function () {
    // turn array buffer into typed array
    var typedarray = new Uint8Array(this.result);

    // create xhttp request to flask server
    var xhttp = new XMLHttpRequest();
    xhttp.open("POST", typedarray, true);
    xhttp.send();
  };
  //Step 3:Read the file as ArrayBuffer
  fileReader.readAsArrayBuffer(file);
  */
}

$("#files").change(handleFileSelect);
