// Needed so that we can track which entry is a camera, and which is a monitor, in case
// of conflicting names
var camOrMonDropDown = []

function newCameraDropdown(valueToSet=null) {
    // Create new drop down element using all allowed cameras the user can access
    // Define element
    var parentAppend = document.getElementById('viewarray');
    var newTableRow = document.createElement('tr');
    var newSelect = document.createElement('select');

    // Put all camreas into options
    for (cam of localcameras) {
        var camOption = document.createElement('option');
        camOption.value = cam
        camOption.text = cam
        newSelect.append(camOption)
    }
    // After options appended, add slot id and cam or mon, do later

    // IF valueToSet is not null, set value
    if (valueToSet != null) {
        newSelect.value = valueToSet
    }

    newTableRow.append(newSelect);
    parentAppend.append(newTableRow);

    camOrMonDropDown.push('cam');
}

function newMonitorDropdown(valueToSet=null) {
    // Create new drop down element using all allowed xbx monitors the user can access
    var parentAppend = document.getElementById('viewarray');
    var newTableRow = document.createElement('tr');
    var newSelect = document.createElement('select');

    // Put all camreas into options
    for (mon of xbxmon) {
        var monOption = document.createElement('option');
        monOption.value = mon
        monOption.text = mon
        newSelect.append(monOption)
    }

    if (valueToSet != null) {
        newSelect.value = valueToSet
    }

    newTableRow.append(newSelect);
    parentAppend.append(newTableRow);

    camOrMonDropDown.push('mon');
}


// On window load, get all info from Server and reconstruct 
function loadSettingsFromDB() {
    var sbox = document.getElementById("secondbox");
    var parentAppend = document.getElementById('viewarray');

    // Take current settings and parse them to existing elements.
    if (loadedMonInfo == "False") {
        // No data, don't do anything
    }
    else {
        // Have data, set seconds and array of view
        loadedMonInfo = (loadedMonInfo.substring(2, loadedMonInfo.length - 2)).split("| ", 3)
        loadedMonInfo[0] = loadedMonInfo[0].replace(/&#39;/g, ''); 
        loadedMonInfo[1] = loadedMonInfo[1].replace(/&#39;/g, '"');
        
        //timeinfo, camarray
        // Loaded in array now, parse JSON at position 2.
        parsedArray = JSON.parse(loadedMonInfo[1]);
        // Now load data into Elements.

        // Load delta time into sbox
        sbox.value =  loadedMonInfo[0].replace('s', '');
       

        // Now we need to programically read each entry in my JSON object and 
        // split type:name, then add the correct drop down type and set the value in it, setting optional 
        // valueToSet

            for (let numKey of Object.keys(parsedArray)) {
                // console.log(numKey)
                // console.log(Object.keys(parsedArray[numKey])[0])

                var data = (Object.keys(parsedArray[numKey])[0])
                var data = data.split(':')
                // Determine type
                if (data[0] == 'cam') {
                    newCameraDropdown(data[1])
                }
                else if (data[0] == 'mon') {
                    newMonitorDropdown(data[1])
                }
            // All loaded!
            }
    }
}

function submitDataToDatabase() {
    // Take values from all existing elements and submit them to server to either add new entry to database
    // OR modify existing entry

    // Get Values from html
    var selectDiv = document.getElementById("viewarray");
    var selectArray = selectDiv.getElementsByTagName('select')
    var sbox = document.getElementById("secondbox").value;
    var sendslotlist = [];
    var monitorName = (window.location.href).split("/");
    monitorName = (monitorName[monitorName.length - 1]);

    // Get list of select elements

    for (let i = 0; i <= (Object.keys(selectArray).length - 1); i++) {
        // sendslotlist is array of just names, assumed slotlist is index in array.
        // Need to differentiate between cameras and monitors, maybe cam, mon:name would work

        if (camOrMonDropDown[i] == 'cam') {
            sendslotlist.push('cam:' + selectArray[i].value);
        }
        else if (camOrMonDropDown[i] == 'mon') {
            sendslotlist.push('mon:' + selectArray[i].value);
        }
    }

    if (sbox == "") {
        // Defaults to 5 seconds
        sbox = 0;
    }
    
    // Create value string in order
    // timeinfo, camarray
    const postString = (
        sbox + "s" + "|" +
        sendslotlist
    )

    fetch('/monitors/slideshowedit/' + monitorName,
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
            if (data == "CREATED" || data == "MODIFIED") {
                window.location.href = ("/monitors/")
            }
    })})
}
