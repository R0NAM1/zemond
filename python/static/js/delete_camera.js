function deleteCameraConfirm(cameraName) {
  var modal = document.getElementById("passwordpopup");
  // For User Reading
  document.getElementById('popup-content').innerHTML = document.getElementById('popup-content').innerHTML.replace('[selectedCamera]', cameraName);
  // For Form Submission
  document.getElementById('form').innerHTML = document.getElementById('form').innerHTML.replace('[selectedCamera]', cameraName);
  
  modal.style.display = "block";
  globalVars.currentCam = cameraName;
}

var globalVars = {};

window.onload = function () {

  // Get the modal
  var modal = document.getElementById("passwordpopup");

  // Get the <span> element that closes the modal
  var span = document.getElementsByClassName('close');

  // When the user clicks on <span> (x), close the modal
  span.onclick = function() {
    modal.style.display = "none";
  }

  // When the user clicks anywhere outside of the modal, close it
  // Pass through variable camera name
  window.onclick = function(event) {
    if (event.target == modal) {
      modal.style.display = "none";
        // For User Reading
      document.getElementById('popup-content').innerHTML = document.getElementById('popup-content').innerHTML.replace(globalVars.currentCam, '[selectedCamera]');
      // For Form Submission
      document.getElementById('form').innerHTML = document.getElementById('form').innerHTML.replace(globalVars.currentCam, '[selectedCamera]');
    }
  } 

};