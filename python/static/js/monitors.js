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

function newmap(newName) {
    // Show upload element below and grab all of that, put it into the db
    var appendMe = document.getElementById('mapAppend');
    // Make upload element
    var uploadElement = document.createElement('input')
    uploadElement.type = 'file';
    uploadElement.accept = 'image/png';
    var imageReader = new FileReader();
    uploadElement.addEventListener('change', () => {
        //Post Request uploading all data, then reload page
        imageReader.onloadend = () => {
            const base64String = imageReader.result.replace('data:', '').replace('/^.+,/', '');
            // POST To upload data, create string
            var postString = 'uploadMap:' + newName + ':' + base64String;
            fetch('/monitors',
                            {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/plain'
                                },
                                body: (postString)
                            }
                            ).then(response => {
                                const data = (response.text())
                                .then(data => {
                                    if (data == "TRUE") {
                                        location.reload();
                                    }
                                    else if (data == "FALSE") {
                                        alert("Error server side inserting into database")
                                    }
                                })})
        };
        var image = event.target.files[0];
        imageReader.readAsDataURL(image);
    })
    // Show element
    appendMe.append(uploadElement);
}

function openTab(tabId) {
    var existTab = document.getElementById("existTab");
    var newTab = document.getElementById("newTab");

    if (tabId == "existTabContent") {
        existTab.style.backgroundColor = "darkgrey";
        newTab.style.backgroundColor = "lightgrey";
        mapTab.style.backgroundColor = "lightgrey";
    }
    else if (tabId == "newTabContent") {
        newTab.style.backgroundColor = "darkgrey";
        existTab.style.backgroundColor = "lightgrey";
        mapTab.style.backgroundColor = "lightgrey";
    }
    else if (tabId == "mapTabContent") {
        newTab.style.backgroundColor = "lightgrey";
        existTab.style.backgroundColor = "lightgrey";
        mapTab.style.backgroundColor = "darkgrey";
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

function deleteMap(mapToDelete) {
    // To be ran when del button is pressed, add extra acknowledgement 
    // Send post request to server, once confirm
    let response = confirm("Are you sure you want to delete this map?");
    if (response) {
    // Send delete request
        fetch('/monitors',
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/plain'
            },
            body: ("deleteMap:" + mapToDelete)
        }
        ).then(response => {
            const data = (response.text())
            .then(data => {
                // If data returns true, reload page
                if (data == "TRUE") {
                    location.reload();
                }
                else if (data == "FALSE") {
                    alert("Server side issue deleting map")
                }
            })})
    }
}

// Want to upload new map
function uploadNew(mapName) {
    // Create input for file type and click from js
    const upload = document.createElement('input');
    upload.type = 'file';
    upload.accept = 'image/png';
    var imageReader = new FileReader();
    upload.addEventListener('change', () => {
        //Post Request uploading all data, then reload page
        imageReader.onloadend = () => {
            const base64String = imageReader.result.replace('data:', '').replace('/^.+,/', '');
            // POST To upload data, create string
            var postString = 'updateMap:' + mapName + ':' + base64String;
            fetch('/monitors',
                            {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/plain'
                                },
                                body: (postString)
                            }
                            ).then(response => {
                                const data = (response.text())
                                .then(data => {
                                    if (data == "TRUE") {
                                        location.reload();
                                    }
                                    else if (data == "FALSE") {
                                        alert("Error server side inserting into database")
                                    }
                                })})
        };
        var image = event.target.files[0];
        imageReader.readAsDataURL(image);
    })
    upload.click();
}

// Confirm delete monitor
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