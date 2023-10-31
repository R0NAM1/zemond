function takexxGenCamSelectArray() {
    var selectArray = document.createElement('ul')
    var x1 = document.getElementById("x1").value;
    var x2 = document.getElementById("x2").value;
    var camArray = document.getElementById("camarray");
    var selectedArray = document.getElementById("arrayselection");
    var finalDbJson = {};
    // Cleanup exisiting cam DOM array if exists

    for (let i = camArray.children.length - 1; i >= 0; i--) {
        let child = camArray.children[i];
        if (child.tagName === 'UL') {
            camArray.removeChild(child);
        }
    }

    
    // Load new data
    camArray.appendChild(selectArray);

    var x3 = Number(x1) * Number(x2)

    // Grab Camera Names
    localcameras = window.localcameras;

    var cameraSelection = document.createElement('select');
    for (let i = 0; i < localcameras.length; i++) {
        // Add camera to array
        let cameraOption = document.createElement('option');
        cameraOption.value = localcameras[i];
        cameraOption.text = localcameras[i];
        cameraSelection.appendChild(cameraOption)
    }
    
    slotList = {};

    // Generate slot options
    for (let i = 1; i <= x3; i++) {
        var optionAppend = document.createElement('li');
        optionAppend.textContent = 'Slot ' + i + '   ';
        // We need to get a dropdown box of all camera names next to each slot, I'll create an element that can be
        // appeneded each time
        
        // Create selection element ID and 
        slotList['slot' + i] = cameraSelection.cloneNode(true);
        slotList['slot' + i].id = ('slot' + i);

        // Put custom ID selection object appended optionAppend
        optionAppend.appendChild(slotList['slot' + i]);

        selectArray.appendChild(optionAppend)   
    }

    // Camera array is generated, can regenerate when called.

}

function loadSettingsFromDB() {
    var x1 = document.getElementById("x1");
    var x2 = document.getElementById("x2");

    // Take current settings and parse them to existing elements.
    if (loadedMonInfo == "False") {
        // console.log("New Monitor, no data to load.")
        takexxGenCamSelectArray();
    }
    else {
        // console.log("Exists, Attempt Parse and Set elements accordingly.")
        loadedMonInfo = (loadedMonInfo.substring(2, loadedMonInfo.length - 2)).split("| ", 3)
        loadedMonInfo[0] = loadedMonInfo[0].replace(/&#39;/g, '');
        loadedMonInfo[1] = loadedMonInfo[1].replace(/&#39;/g, '');
        loadedMonInfo[2] = (loadedMonInfo[2]).replace(/&#39;/g, '"');
        //lengthbywidthnum, timeinfo, camarray
        // console.log(loadedMonInfo)
        // Loaded in array now, parse JSON at position 2.
        parsedArray = JSON.parse(loadedMonInfo[2])
        // Now load data into Elements.
        // console.log(loadedMonInfo[0].split("x", 2))
        var x = loadedMonInfo[0].split("x", 2)
        // console.log(x[0] + ':' + x[1])
        // console.log(parsedArray)

        // Load xbx into x1 and x2
        x1.value = x[0]
        x2.value = x[1]

        // Load elements based on selection, now that it's set:
        takexxGenCamSelectArray();

        // Now that selection array boxes are loaded, loop and load array.

        for (let numKey of Object.keys(parsedArray)) {
            // console.log(numKey)
            let numCam = Object.keys(parsedArray[numKey])[0]
            // console.log(numCam)

            // Now we have all the info, assign to specific slot[i]
            // console.log("slot" + numKey);
            let slotElement = document.getElementById("slot" + numKey);
            slotElement.value = numCam;
        }

    }
}

function submitDataToDatabase() {
    // Take values from all existing elements and submit them to server to either add new entry to database
    // OR modify existing entry

    // Get Values
    var x1 = document.getElementById("x1").value;
    var x2 = document.getElementById("x2").value;
    var sendslotlist = [];
    var monitorName = (window.location.href).split("/");
    monitorName = (monitorName[monitorName.length - 1]);

    for (let i = 1; i <= Object.keys(slotList).length; i++) {
        // sendslotlist is array of just names, assumed slotlist is index in array.

        sendslotlist.push((slotList["slot" + i]).value)
    
    }

    

   
    sbox = 0
    

    // Create value string in order
    //lengthbywidthnum, timeinfo, camarray
    const postString = (
        x1 + "x" + x2 + "|" +
        sbox + "s" + "|" +
        sendslotlist
    )


    fetch('/monitors/xbxedit/' + monitorName,
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
