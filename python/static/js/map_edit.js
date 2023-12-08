var buttonArray = [];
var buttonDownCurrent = null;
var currentFloorEditing = null;
var globalFloorArrayVolitile = [];
var localcameras = null;

// How to store current edit floors as volitile?
// Need to store floor name, map used, and buttons with % positions
// Array in array?
// Array of arrays in specific config
// [name, map, [camUsedForButton,Width%, Height%], [camUsedForButton,Width%, Height%], etc]
// Any array entry above 1 is a camera button, 
// The above array goes into globalFloorArrayVolitile, each entry in array is assumed to be a floor
// globalFloorArrayVolitile is updated every mouseup event, 
// When edit is pressed, loop over globalFloorArrayVolitile to find name, and load information from there
// Duplicate names not allowed, loop and check every new floor.

// Create new floor, add to globalFloorArrayVolitile with no data
function newFloorLevel(existingName, existingMap) {
    // Verify box has data
    if (document.getElementById('floorName').value || existingName) {
        // Element to append to
        var appendFloorDiv = document.getElementById('floorarray');
        // New table row for this floor
        var floorRow = document.createElement('tr');

        // New elements, floor name and maps available as select element
        var floorNameElement = document.createElement('h4');

        // If passing in an existing name, use that, else go by textBox
        if (existingName) {
            floorNameElement.textContent = existingName;
        }
        else {
            floorNameElement.textContent = document.getElementById('floorName').value;
        }

        // Create drop down of all maps
        var mapsDropDown = document.createElement('select');

        // Add all select options for dropdown, names of the maps
        // Split mapData into array and process each as option element
        // Tracking index
        var i = 0;

        // Create options for select
        for (data of mapData) {
            // Surrounded by (), remove
            data = data.slice(1, -1);
            // Surrounded by "", remove by replacing
            data = data.replaceAll('"', '');
            // One entry, split into name 0, image 1 as base64
            data = data.split(',');
            // Data formatted, put into option element
            var newOption = document.createElement('option');
            newOption.value = i;
            newOption.text = data[0];
            // Add option to select
            i++;
            mapsDropDown.append(newOption);
        }
        
        if (existingMap) {
            // Is set on itterable i, loop over options text value until matches, then set
            var i = 0;
            for (option of mapsDropDown) {
                if (option.text == existingMap) {
                    mapsDropDown.value = i;
                }
                i++
            }
        }

        // Create TDS for floorname, dropdown
        var floorNameTD = document.createElement('td');
        floorNameTD.append(floorNameElement);
        floorRow.append(floorNameTD);

        var mapDropDownTD = document.createElement('td');
        mapDropDownTD.append(mapsDropDown);
        floorRow.append(mapDropDownTD);

        // Edit select, for each floor to add cameras and place buttons
        var radioTD = document.createElement('td');
        var radioInput = document.createElement('input');
        radioInput.type = 'button';
        radioInput.value = 'Edit';
        radioInput.onclick = function() {
            editFloor(floorNameElement.textContent, mapsDropDown.value);
            }
        radioTD.append(radioInput);
        floorRow.append(radioTD);

        // Append row to table
        appendFloorDiv.append(floorRow);

        // Add to globalFloorArrayVolitile [name, map, [camUsedForButton,Width%, Height%]
        var tempFloorArrayEmpty = [];
        // Push name
        tempFloorArrayEmpty.push(document.getElementById('floorName').value);
        
        // Push tempArray to global
        if (!existingName) {
            globalFloorArrayVolitile.push(tempFloorArrayEmpty);
        }
    }
}


function attemptNewCamera() {
    // If editing floor, allow new camera
    if (currentFloorEditing) {
        // Can add a new camera
        var mapEditDiv = document.getElementById('mapEditDiv');

        // Attempt to create a new camera button that is draggable within mapEditDiv, location in % is saved
        var newButton = document.createElement('div');
        newButton.style.display = 'inline-block';
        newButton.style.border = '1px solid #000';
        newButton.style.backgroundColor = '#dedede';
        newButton.style.padding = '5px 10px';
        newButton.style.cursor = 'pointer';
        newButton.style.position = 'absolute';
        newButton.style.textAlign = 'center';
        newButton.id = 'cambutton';
        newButton.textContent = 'Cam ' + (buttonArray.length + 1);
        // buttonArray being the buttons present on the currentFloorEditing
        buttonArray.push(newButton);

        // Append newButton to body
        var appendBody = document.body;
        appendBody.append(newButton);

        // Set initial point, top left of mapEditDiv
        newButton.style.left = mapEditDiv.offsetLeft + 'px';
        newButton.style.top = mapEditDiv.offsetTop + 'px';
        
        // When mouse down on this element, set global am mouse down.
        newButton.addEventListener('mousedown', function(e) {
            buttonDownCurrent = newButton;
            document.body.style.userSelect = 'none';
        }, true)

        // Add new entry to cameraButtonAssoc
        var cameraButtonAssoc = document.getElementById('cameraButtonAssoc');
        // Create row in table
        var newAssocRow = document.createElement('tr');
        // Column 1, camera button index
        var col1 = document.createElement('td');
        col1.textContent = 'Cam ' + (buttonArray.length);
        // Append to row
        newAssocRow.append(col1);

        // Column 2, selection element for all available cameras to user
        var col2 = document.createElement('td');
        var newSelectElement = document.createElement('select');

        for (cam of localcameras) {
            var newOption = document.createElement('option');
            newOption.text = cam;
            newOption.value = cam;
            // Append new option to select
            newSelectElement.append(newOption);
        }

        // Append finished select element to column
        col2.append(newSelectElement);
        newAssocRow.append(col2);

        // Append row to table
        cameraButtonAssoc.append(newAssocRow);
    }
}


function editFloor(floorNameElement, mapToEdit) {
    // Set current floo I am editing to floorNameElement
    currentFloorEditing = floorNameElement;

    // Clear mapEditDiv and append mapToEdit image, then load camera coords and buttons
    var mapEditDiv = document.getElementById('mapEditDiv');

    // Remove all elements under mapEditDiv, usually just img 
    while (mapEditDiv.firstChild) {
        mapEditDiv.firstChild.remove();
    }

    // Create image
    var mapImage = document.createElement('img');

    // Depending on mapToEdit, get base64 received from server
    indexData = mapData[mapToEdit]
    // Process data
    indexData = indexData.split(', ');
    indexData = indexData[1].replaceAll('"', '');
    indexData = indexData.replaceAll(')', '');
    // Set image, and static consistant width
    var imageBase64 = (indexData)
    mapImage.src = ('data:image/png;base64,' + imageBase64);
    mapImage.width = 600;

    // Append to mapEditDiv
    mapEditDiv.append(mapImage);

    
    // Replace cameraButtonAssoc with what is currently saved to globalFloorArrayVolitile
    // Attempt to find the current floor saving in globalFloorArray
    for (floorArray of globalFloorArrayVolitile) {
        // Check if current floorArray name is the one I am editing 
        thisFloorArrayName = floorArray[0];
        
        if (currentFloorEditing == thisFloorArrayName) {
            // Floor I am editing exists already, override existing data
            // Remove all cambutton class objects and re-add depending on array data
            // Grab all existing camera buttons
            var allCamButtonByID = document.querySelectorAll('#cambutton');
            
            // Remove those buttons
            for (button of allCamButtonByID) {
                button.remove();            
            }
            
            // Reset buttonArray for this floor
            buttonArray = [];
            
            // Remove all existing camera array association select elements
            var cameraButtonAssoc = document.getElementById('cameraButtonAssoc');
            cameraButtonAssoc.innerHTML = "";
            
            // Removed! Redraw all buttons and set positions
            // Buttons present in index 2 and above
            
            // Need to re-add camera buttons now, go though current floorArray and pull buttons (+2 on the index, as all button data is offset
            // that much) 
            var currentButtonDataIndex = 0;

            while ((floorArray.length - 2) > currentButtonDataIndex) {
                // Now parsing a (valid!) button array
                // Camera name, x, y
                // Reconstruct button element, camAssocElements and set position in document
                // Reconstruct:
                var mapEditDiv = document.getElementById('mapEditDiv');
                
                // Reconstruct camera button from existing data, taking % data and calculating pixel data for it
                let newButton = document.createElement('div');
                newButton.style.display = 'inline-block';
                newButton.style.border = '1px solid #000';
                newButton.style.backgroundColor = '#dedede';
                newButton.style.padding = '5px 10px';
                newButton.style.cursor = 'pointer';
                newButton.style.position = 'absolute';
                newButton.style.textAlign = 'center';
                newButton.id = 'cambutton';
                newButton.textContent = 'Cam ' + (currentButtonDataIndex + 1);
                // Push to currentfloorarray
                buttonArray.push(newButton);
                
                // Add button to document body
                var appendBody = document.body;
                appendBody.append(newButton);
                
                // PercentAndPixel equation variables
                var mapEditDiv = document.getElementById('mapEditDiv');
                // Top left of mapEditDiv
                var mapEditDivXOrigin = mapEditDiv.offsetLeft;
                var mapEditDivYOrigin = mapEditDiv.offsetTop;
                // Bottom right of mapEditDiv
                var mapEditDivHeightAbsolute = (mapEditDivYOrigin + mapEditDiv.offsetHeight);
                var mapEditDivWidthAbsolute = (mapEditDivXOrigin + mapEditDiv.offsetWidth);
                // Existing data to grab from array
                var percentX = (floorArray[currentButtonDataIndex + 2])[1];
                var percentY = (floorArray[currentButtonDataIndex + 2])[2];
                
                // Calculate pixel position for button
                var buttonOffsetLeft = (percentX / 100) * (mapEditDivWidthAbsolute - mapEditDivXOrigin) + mapEditDivXOrigin;
                var buttonoffsetTop = (percentY / 100) * (mapEditDivHeightAbsolute - mapEditDivYOrigin) + mapEditDivYOrigin;
                
                // Set calculated button position
                newButton.style.left = buttonOffsetLeft + 'px';
                newButton.style.top = buttonoffsetTop + 'px';
                
                // Add event handler to button for dragging
                newButton.addEventListener('mousedown', function(e) {
                    buttonDownCurrent = newButton;
                    document.body.style.userSelect = 'none';
                }, true);
                
                // Add new entry to cameraButtonAssoc
                var cameraButtonAssoc = document.getElementById('cameraButtonAssoc');
                
                // Create row in table
                var newAssocRow = document.createElement('tr');
                
                // Column 1, camera button index, set camera number
                var col1 = document.createElement('td');
                col1.textContent = 'Cam ' + (buttonArray.length);
                
                // Append to row
                newAssocRow.append(col1);
                
                // Column 2, selection element for all available cameras to user
                var col2 = document.createElement('td');
                var newSelectElement = document.createElement('select');
                
                // Loop over localcameras and create all option elements to put into select
                for (cam of localcameras) {
                    var newOption = document.createElement('option');
                    newOption.text = cam;
                    newOption.value = cam;
                    // Append new option to select
                    newSelectElement.append(newOption);
                }
                
                // Append finished select element to column
                col2.append(newSelectElement);
                newAssocRow.append(col2);
                
                // Set current select element option to floorArray one according to currentButtonDataIndex
                var selectedCameraFromArray = (floorArray[currentButtonDataIndex + 2])[0];
                newSelectElement.value = selectedCameraFromArray;
                
                // Append row to table
                cameraButtonAssoc.append(newAssocRow);
                
                // Increase index to go to next button
                currentButtonDataIndex++;
            }
        }
    }
}


// On window load, get all info from Server and reconstruct data, also set saving event handlers
function loadSettingsFromDB() {
    // Process server data
    mapData = mapData.replace(/&#39;/g, '"')
    mapData = mapData.split('|');
    // On load, process to localcameras array 
    localcameras = (window.localcameras).split('|');
    
    // Event handler to handle on mouseup, not dragging button anymore, userSelect reset, and saving current modified data to global array   
    document.addEventListener('mouseup', function(e) {
        // Not dragging a button, reset userSelect for text selection
        buttonDownCurrent = null;
        document.body.style.userSelect = 'auto';

        // Copy globalFloorArrayVolitile, so no infinate loop
        var globalFloorArrayVolitileCopy = [];
        for (floorArray of  globalFloorArrayVolitile) {
            globalFloorArrayVolitileCopy.push(floorArray);
        }

        // (Template for array)
        // [name, map, [camUsedForButton,Width%, Height%], [camUsedForButton,Width%, Height%], etc]
        // Only save current floor if there is a current floor to save
        if (currentFloorEditing) {
            // Have a floor to store, do it!
            // Need to check if we already have this floor in array
            var doesFloorAlreadyExist = false;
            // If not in globalFloorArrayVolitile, push to next available index
            // If is, then edit at index, 
            // Loop through globalFloorArrayVolitile for floor name, index 0   

            for (floorArray of globalFloorArrayVolitileCopy) {
                // Inspect current floor array to see if editing existing
                // Grab name for current floor array
                thisFloorArrayName = floorArray[0];
                // Does the floor I am currently editing already exist in my saved array?
                if (currentFloorEditing == thisFloorArrayName) {
                    // Floor has already been saved! Edit that instead of pushing new data
                    doesFloorAlreadyExist = true;
                }
            }

            // If floor already exists, then reconstruct data and overwrite data in index where data already exists
            if (doesFloorAlreadyExist) {
                // Only updating map, and button
                // Grab array from globalFloorArrayVolitile
                // Tracking variable, where to push final array
                var arrayIndex = 0;

                for (floorArray of globalFloorArrayVolitileCopy) {
                    // Inspect current floor array to see if editing existing
                    thisFloorArrayName = floorArray[0];
                    if (currentFloorEditing == thisFloorArrayName) {
                        // This is the array I want to edit
                        var tempFloorArray = [];
                        // Push 0, name
                        tempFloorArray.push(currentFloorEditing)

                        // Push 1, mapName
                        // Get mapName from <tr> row with first <td> as floorName
                        var floorTableElement = document.getElementById('floorarray');
                        var floorRows = floorTableElement.querySelectorAll('tr');
                        
                        // Loop over existing rows in floorRows, attempting to find mapImage name
                        floorRows.forEach(row => {
                            // Verify this row is the floor requested
                            var firstTd = row.querySelector('td');

                            if (firstTd.textContent == currentFloorEditing) {
                                //Correct Floor Row! Grab select element map name

                                let floorSelectElement = row.querySelectorAll('td')[1].querySelector('select');
                                // Have select element, grab textContent and push as index 1
                                // Content is grabbed by getting the selectedIndex number and selecting the option element from that
                                var currentOption = floorSelectElement.options[floorSelectElement.selectedIndex];
                                tempFloorArray.push(currentOption.text);
                            }
                        });

                        // Two defined vars pushed, now grab each button element, positions, and store
                        // Done by grabbing all same ids and only applying logic to thise with 'Cam'
                        var allCamButtonByID = document.querySelectorAll('#cambutton');
                        var indexCurrent = 0;

                        // Camera assoc div
                        var camAssocTable = document.getElementById('cameraButtonAssoc');

                        // PixelPercent equation variables
                        var mapEditDiv = document.getElementById('mapEditDiv');
                        // Top left of mapEditDiv
                        var mapEditDivXOrigin = mapEditDiv.offsetLeft;
                        var mapEditDivYOrigin = mapEditDiv.offsetTop;
                        // Bottom Right of mapEditDiv
                        var mapEditDivHeightAbsolute = (mapEditDivYOrigin + mapEditDiv.offsetHeight);
                        var mapEditDivWidthAbsolute = (mapEditDivXOrigin + mapEditDiv.offsetWidth);
                    
                        // Loop over buttons
                        for (button of allCamButtonByID) {
                            var thisButtonArray = [];
                            // [camUsedForButton,Width%, Height%]
                            // camUsedForButton is the current index of the camera (Cam 1)
                            var wantedRow = camAssocTable.rows[indexCurrent];
                            var selectTD = wantedRow.cells[1];
                            var innerSelectTD = selectTD.querySelector('select');
                            // Have camUsedForButton (localcamera), push to array now
                            thisButtonArray.push(innerSelectTD.value);

                            // Top left is 0, 0, take mapEditDiv top left and treat as origin,
                            // from 'origin', take coords of button and compare TO percentage
                            // Take current button position and take away the origin as an offset, of1 is distance from origin
                            // Take map width/length, takeing away the origin, to get of2 as a zeroed point to make consistant(?)
                            // Devide of1 by of2 to get the decimal value of the final offset, and times by 100 to make percentage value

                            // Run calculation
                            var percentX = ((button.offsetLeft - mapEditDivXOrigin) / (mapEditDivWidthAbsolute - mapEditDivXOrigin)) * 100;
                            var percentY = ((button.offsetTop - mapEditDivYOrigin) / (mapEditDivHeightAbsolute - mapEditDivYOrigin)) * 100;

                            // Now push X and Y to array
                            thisButtonArray.push(percentX);
                            thisButtonArray.push(percentY);

                            //Data array complete, save to floor array
                            tempFloorArray.push(thisButtonArray);

                            // Itteration complete, increase index
                            indexCurrent++;
                        }
                        
                        // Based on arrayIndex, push to globalFloorArrayVolitile
                        globalFloorArrayVolitile[arrayIndex] = tempFloorArray;
                    }
                    // Increase arrayIndex
                    arrayIndex++;
                }
            }

            // If floor does NOT exist in globalFloorArray, add to end of array
            else {
                //Construct new floor array for current edit floor
                var tempFloorArray = [];
                // Push 0, name
                tempFloorArray.push(currentFloorEditing)

                // Push 1, mapName
                // Get mapName from <tr> row with first <td> as floorName
                var floorTableElement = document.getElementById('floorarray');
                var floorRows = floorTableElement.querySelectorAll('tr');

                // Loop over existing rows in floorRows, attempting to find mapImage name
                floorRows.forEach(row => {
                    // Verify this row is the floor requested
                    var firstTd = row.querySelector('td');

                    if (firstTd.textContent == currentFloorEditing) {
                        //Correct Floor Row! Grab select element map name

                        let floorSelectElement = row.querySelectorAll('td')[1].querySelector('select');
                        // Have select element, grab textContent and push as index 1
                        // Content is grabbed by getting the selectedIndex number and selecting the option element from that
                        var currentOption = floorSelectElement.options[floorSelectElement.selectedIndex];
                        tempFloorArray.push(currentOption.text);
                    }
                });

                // Two defined vars pushed, now grab each button element, positions, and store
                // Done by grabbing all elements with certain ID and only applying logic to those with 'Cam'
                var allCamButtonByID = document.getElementsByClassName('cambutton');
                var indexCurrent = 0;

                // Camera assoc div
                var camAssocTable = document.getElementById('cameraButtonAssoc');

                // PixelPercent equation variables
                var mapEditDiv = document.getElementById('mapEditDiv');
                // Top left of mapEditDiv
                var mapEditDivXOrigin = mapEditDiv.offsetLeft;
                var mapEditDivYOrigin = mapEditDiv.offsetTop;
                // Bottom Right of mapEditDiv
                var mapEditDivHeightAbsolute = (mapEditDivYOrigin + mapEditDiv.offsetHeight);
                var mapEditDivWidthAbsolute = (mapEditDivXOrigin + mapEditDiv.offsetWidth);
            
                // Loop over buttons
                for (button of allCamButtonByID) {
                    var thisButtonArray = [];
                    // [camUsedForButton,Width%, Height%]
                    // camUsedForButton is the current index of the camera (Cam 1)
                    var wantedRow = camAssocTable.rows[indexCurrent];
                    var selectTD = wantedRow.cells[1];
                    var innerSelectTD = selectTD.querySelector('select');
                    // Have camUsedForButton (localcamera), push to array now
                    thisButtonArray.push(innerSelectTD.value);

                    // Top left is 0, 0, take mapEditDiv top left and treat as origin,
                    // from 'origin', take coords of button and compare TO percentage
                    // Take current button position and take away the origin as an offset, of1 is distance from origin
                    // Take map width/length, takeing away the origin, to get of2 as a zeroed point to make consistant(?)
                    // Devide of1 by of2 to get the decimal value of the final offset, and times by 100 to make percentage value

                    // Run calculation
                    var percentX = ((button.offsetLeft - mapEditDivXOrigin) / (mapEditDivWidthAbsolute - mapEditDivXOrigin)) * 100;
                    var percentY = ((button.offsetTop - mapEditDivYOrigin) / (mapEditDivHeightAbsolute - mapEditDivYOrigin)) * 100;

                    // Now push X and Y to array
                    thisButtonArray.push(percentX);
                    thisButtonArray.push(percentY);

                    //Data array complete, save to floor array
                    tempFloorArray.push(thisButtonArray);

                    // Itteration complete, increase index
                    indexCurrent++;
                }

                // Temp Floor Array Done! Push to globalFloorArrayVolitile
                globalFloorArrayVolitile.push(tempFloorArray);
            }            
        }

        // End of mouseup events
    }, true)

    // When moving mouse, check if on a button, if so allow movement
    // Add an event listener for the 'mousemove' event on the container
    document.addEventListener('mousemove', function(event) {
        // Prevent the default action of the event
        event.preventDefault();

        // Get top left coords of mapEditDiv, get lxw and calculate draggable area
        var mapEditDiv = document.getElementById('mapEditDiv');
        // Top left of mapEditDiv
        var mapEditDivX = mapEditDiv.offsetLeft;
        var mapEditDivY = mapEditDiv.offsetTop;

        // mapEditDiv width and height
        var mapEditDivWidth = mapEditDiv.offsetWidth;
        var mapEditDivHeight = mapEditDiv.offsetHeight;
        
        // Bottom right of mapEditDiv
        var finalX = mapEditDivX + mapEditDivWidth;
        var finalY = mapEditDivY + mapEditDivHeight;
        
        // If we are mousedown of a valid button
        if (buttonDownCurrent) {
            
            // Get current coords of the mouse
            var mouseX = event.clientX;
            var mouseY = event.clientY;

            // If in draggable area, move X
            if ((mouseX > mapEditDivX) && (mouseX < finalX)) {

                // Get current padding of button, process and calc half of button
                var fullPad = (buttonDownCurrent.style.padding);
                fullPad = fullPad.replaceAll('px', '')
                fullPad = fullPad.split(' ');

                // Process new XY coords for button
                mouseX = (mouseX - fullPad[0]);

                // Set new position for element, add px to specify unit
                buttonDownCurrent.style.left = (mouseX + 'px');
            }

            // If in draggable area, move Y
            if ((mouseY > mapEditDivY) && (mouseY < finalY) ) {
                // Get current padding of button, process and calc half of button
                var fullPad = (buttonDownCurrent.style.padding);
                fullPad = fullPad.replaceAll('px', '')
                fullPad = fullPad.split(' ');

                // Process new XY coords for button
                mouseY = (mouseY - fullPad[1]);

                // Set new position for element, add px to specify unit
                buttonDownCurrent.style.top = (mouseY + 'px');
            }
        }
        // End of mousemove event
    }, true)

    // Event initialization done, loadDB info now
    // Take current settings and parse them to existing elements.
    if (loadedMonInfo == "False") {
        // No data, don't do anything
    }

    else {
        // Have data, set globalDataArrayVolitile
        loadedMonInfo = loadedMonInfo.replace(/&#39;/g, '"');
        // loadedMonInfo = (loadedMonInfo.substring(2, loadedMonInfo.length - 3)).split("|")
        loadedMonInfo = loadedMonInfo.split("|");
        
        // For every floorArray, take data and load it into globalFloorArrayVolitile, array by array, and then force generate
        // elements based on globalFloorArray
        for (array of loadedMonInfo) {
            var validArray = (JSON.parse(array));
            // Valid floor array, (I think,) append to globalFloorArrayVolitile
            globalFloorArrayVolitile.push(validArray)

            // Load this array data into site, start with editFloor

            var floorName = validArray[0];
            var mapName = validArray[1];

            newFloorLevel(floorName, mapName);
        }
    }
}

function submitDataToDatabase() {
    //Temp, show coords of all buttonArrayButtons

    console.log(globalFloorArrayVolitile)
    // Take globalFloorArrayVolitile and POST request to server for saving. is part of postString

    // Get Values from html
    var monitorName = (window.location.href).split("/");
    monitorName = (monitorName[monitorName.length - 1]);
    
    // Create value string in order
    // globalFloorArray
    const postString = (
        JSON.stringify(globalFloorArrayVolitile)
    )

    fetch('/monitors/mapmonedit/' + monitorName,
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
