monitorToDelete = 'none';

function xbxedit(monname) {
    console.log(monNewName.value)
    if (monNewName.value){
        location.href = ('/monitors/xbxedit/' + monname)
    }
    else if (monNewName.value == '') {
        
    }
}

function slideshowedit(monname) {
    console.log(monNewName.value)
    if (monNewName.value){
        location.href = ('/monitors/slideshowedit/' + monname)
    }
    else if (monNewName.value == '') {
        
    }
}

function openTab(tabId) {
    var existTab = document.getElementById("existTab");
    var newTab = document.getElementById("newTab");

    if (tabId == "existTabContent") {
        existTab.style.backgroundColor = "darkgrey";
        newTab.style.backgroundColor = "lightgrey";
    }
    else if (tabId == "newTabContent") {
        newTab.style.backgroundColor = "darkgrey";
        existTab.style.backgroundColor = "lightgrey";
    }

    // Hide all tab contents
    var tabContents = document.getElementsByClassName("tab-content");
    for (var i = 0; i < tabContents.length; i++) {
      tabContents[i].classList.remove("show");
    }
  
    // Show the selected tab content
    var selectedTabContent = document.getElementById(tabId);
    selectedTabContent.classList.add("show");
    
}

function xbxmondropdown() {
    document.getElementById('xbxmondropdowncontent').classList.toggle("show");
}

function slideshowdropdown() {
    document.getElementById('slideshowdropdowncontent').classList.toggle("show");
}

function mapmondropdown() {
    document.getElementById('mapmondropdowncontent').classList.toggle("show");
}

function deleteMonitor(monToDelete) {
    // To be ran when del button is pressed, add extra acknowledgement 
    appendMsgDiv = document.getElementById("absoluteDelConfirm");
    appendMsgDiv.style.display = 'block';
    console.log("Wanna delete " + monToDelete)
    // Send post request to server, once confirm
    monitorToDelete = monToDelete;
}

function confirmDeleteForQueue() {
    // Gets set monitor id and sends delete request to server
    fetch('/monitors',
    {
        method: 'POST',
        headers: {
            'Content-Type': 'application/plain'
        },
        body: ("deleteMonitor:" + monitorToDelete)
    }
    ).then(response => {
        const data = (response.text())
        .then(data => {
            // If data returns true, reload page
            document.getElementById('absoluteDelConfirm').style.display = 'none';

            if (data == "TRUE") {
                location.reload();
            }

        })})
}