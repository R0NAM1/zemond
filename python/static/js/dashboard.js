function loadOther() {

  // Load Threads
  // Grab select and interpret to array 
  var threadsArray = (window.threadsArray).replace(/&#39;/g, '"');
  threadsArray = (threadsArray).replace(/&lt;/g, '<');
  threadsArray = (threadsArray).replace(/&gt;/g, '>');
  threadsArray = eval(threadsArray);
  
  // Select element and append elements
  var parentDiv = document.getElementById('threadsactiveDropdown');

  for (var thread of threadsArray) {
    var threadEleDiv = document.createElement('div');
    threadEleDiv.className = 'subdataThreads';

    threadEleDiv.innerText = thread;
    parentDiv.appendChild(threadEleDiv);
  }

  // Load User Array
  var sessionsArray = (window.sessionsArray).replace(/&#39;/g, '"');
  console.log(sessionsArray)
  sessionsArray = eval(sessionsArray);


  // Get and apply number
  var userLength = sessionsArray.length

  var ulHeader = document.getElementById('userhead');
  ulHeader.innerText = ("User Sessions: " + userLength)

  // Create length
  var dropDown = document.getElementById('userDropdown');

  for (var session of sessionsArray) {
    var sessionEleDiv = document.createElement('div');
    sessionEleDiv.className = 'subdataUsers';

    sessionEleDiv.innerText = session;
    dropDown.appendChild(sessionEleDiv);
  }
}

window.onload = loadOther;