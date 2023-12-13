import '/static/node_modules/webrtc-adapter/out/adapter.js';
import { stunServer } from '/static/js/stunServer.js';
// Adapter JS takes over certain functions if needed, for browser cross-compatability.
// You just include it and it does the rest.
// Import Stun Server URL from seperate JS file

var pc = null, dcInterval = null; 
var currentFloorIndex = 0;
var camarray = null;
var dbinfo = null;
var camNameArray = [];
var videoTrackArray = [];
var serverSDPAnswer = null;
var incomingTrackIndexTracker = 0;

// In this file, create a video element for the background and reconstruct the mapData into a FNAF style map overlay for ease
// of use

// Sleep function for when needed
function sleepForMiliseconds(miliseconds) {
    return new Promise(resolve => setTimeout(resolve, miliseconds));
}

// Negotiate with server for WebRTC streams
async function negotiate() {
    // Send offer to server for WebRTC
    return pc.createOffer({iceRestart:true}).then(function(offer) {

        return pc.setLocalDescription(offer); // I am the offer.
    }).then(function() {
        // wait for ICE gathering to complete
        return new Promise(function(resolve) {
            if (pc.iceGatheringState === "complete") {
                resolve();
            } else {
                function checkState() {
                    if (pc.iceGatheringState === "complete") {
                        pc.removeEventListener(
                            "icegatheringstatechange",
                            checkState
                        );
                        resolve();
                    }
                }
                pc.addEventListener("icegatheringstatechange", checkState);
            }
        });
    }).then(function() {
        // When ICE Gatherin is now complete. send SDP offer to server
        var offer = pc.localDescription; // Send our offer to the server in a JSON format, we expect a raw ANSWER, not encapsulated,
        return fetch('/monitors/offer/' + window.monitor, {
            body: JSON.stringify({
                sdp: offer.sdp,
                type: offer.type,
            }),
            headers: {
                'Content-Type': 'application/json'
            },
            method: 'POST'
        });
    }).then(function(response) {
        return response.json();
    }).then(function(answer) {
        // Make answer from server globally available
        serverSDPAnswer = answer;

        var sess = new RTCSessionDescription(answer) // Set Session Description Object to Server Answer
        return pc.setRemoteDescription(sess);   //Finally, set the remote peers description.
    })
}


// Autorun once document initialization is done
async function startWebRtcStreamsAndAttatch(camNameArray) {
    console.log("Detected Browser As: " + adapter.browserDetails.browser + " " + adapter.browserDetails.version)
    var config = {
        sdpSemantics: 'unified-plan', // Modern SDP format.
        iceServers: [stunServer] //This will be dynamic based on server config later
    };

    pc = new RTCPeerConnection(config); // Set server to config

    // Push video streams to correct index based on ssrc
    pc.addEventListener('track', async function(evt) {
        // Only called when a track is added, should happen per transceiver.
        if (evt.track.kind == 'video') {
            // Should get incoming track here, make it it's own object, cannot use embedded streams[0] object.
            let incomingStream = new MediaStream([evt.track]); // Set video object stream to object

            //Get transceiver according to this event
            let transceiver = evt.transceiver;

            // If incomingTrackIndexTracker is 0, means first track is here, autoconnect to have something on the screen
            if (incomingTrackIndexTracker == 0) {
                var videoElement = document.getElementById('videoElement');
                videoElement.srcObject = incomingStream;
            }
            
            // Wait for transceiver to establish full connection to client
            await sleepForMiliseconds(500)

            // Set SSRC for this transceiver
            let thisSsrc = null;
            let stats = await transceiver.receiver.getStats();
            for (let report of stats.values()) {
                // If correct report type, get SSRC for unique stream identification    
                if (report.type === 'inbound-rtp') {
                    thisSsrc = report.ssrc;
                }
            }

            // Depending on SSRC, push track to index in videoTrackArray that is the same index as ssrcAssoc
            // ssrcAssoc is originally from server, included in SDP response
            var ssrcAssocArray = serverSDPAnswer.ssrcAssoc;

            // Loop through each ssrc from the server, find which one matches according to index, and push incomingStream
            // to videoTrackArray based on that index, final result should have videoTrackArray, ssrcAssocArray, and camNameArray
            // all synced by index
            var ssrcIndexTrack = 0;
            for (var ssrc of ssrcAssocArray) {
                // If equals
                if (ssrc == thisSsrc) {
                    // Debug
                    // console.log("Pushing SSRC " + ssrc + " to index " + ssrcIndexTrack)
                    // Push to array based on index
                    videoTrackArray[ssrcIndexTrack] = incomingStream;
                }
                ssrcIndexTrack++;
            }

            // Processed another stream, add one to tracker so we know how many we have
            incomingTrackIndexTracker++;
        }
    });

    // Define datachannel object and global pc and dc object
    let dc = pc.createDataChannel('chat') 
    let globalPcObject = pc;
    let globalDcObject = dc;
    // Closing case
    dc.onclose = function() {
        clearInterval(dcInterval);
        dataChannelLog.textContent += '- close\n';
    };
    dc.onopen = function() {
        // Set interval to ping every second
        dcInterval = setInterval(function() {
            var message = 'ping';
            dc.send(message);
        }, 1000);
    };

    for (var camName of camNameArray) {
        pc.addTransceiver('video', {direction: 'recvonly'}); // We only receive video

        // Initialize videoTrackArray with all nulls to length of camNameArray
        videoTrackArray.push(null);
    }

    // Negotiate clients and connect peers
    negotiate(); 
}

// Called when camera button is pressed, use camera name for ease of selection
function changeActiveCameraByName(camname) {
    // console.log("Want to change camera by name to " + camname);

    var videoElement = document.getElementById('videoElement');
    // Find index of camname in camNameArray

    // If cameraname is equal to that of array, use resulting trackIndex to set video
    var trackIndex = 0;
    for (var camName of camNameArray) {
        if (camName == camname) {
            // Set source
            videoElement.srcObject = videoTrackArray[trackIndex];
        }
        trackIndex++;
    }
}

function changeFloorMap(direction) {
    // By default we start on index 0, tracking currentFloorIndex

    if (currentFloorIndex < 0) {
        console.log("Cannot hold what does not exist!")
    }
    else if (currentFloorIndex >= 0) {

        if ((direction == 'left') && (currentFloorIndex > 0) ) {
            currentFloorIndex--;
        }
        else if ((direction == 'right') && (currentFloorIndex < (camarray.length - 1))) {
            currentFloorIndex++;
        }

        // Index sorted, change elements to reflect new floor selected
        // Change elemtent if centerFloorText textContent to reflect
        var floorArray = JSON.parse(camarray[currentFloorIndex]);

        var centerFloorTextElement = document.getElementById('centerFloorText');
        centerFloorTextElement.textContent = floorArray[0];

        // Now hide all floorDiv:0-oo elements
        for (var trackIndex in camarray) {
            var thisElement = document.getElementById('floorDiv:' + trackIndex);
            thisElement.style.display = 'none';
        }

        // Show only the floorDiv I want
        var floorDiv = document.getElementById('floorDiv:' + currentFloorIndex);
        floorDiv.style.display = 'block';

        // Change height of mapHoldDiv to height of image within my floorDiv
        var mapHoldDiv = document.getElementById('mapHoldDiv');
        var wantedHeight = floorDiv.querySelector('img').height;

        mapHoldDiv.style.height = wantedHeight + 'px';
    }

}

// Load on window.load
export function loadMonitor() {
    // Add all video elements and assign IDS for WebRTC array.
    // Replace " with nothing or ".
    dbinfo = (window.dbinfo).replace(/&#39;/g, '"')
    camarray = String((window.camarray).replace(/&#39;/g, '"'))

    camarray = camarray.split("|");
    dbinfo = dbinfo.split("|");

    var tmpArray = [];

    // Get DBINFO in usable state

    for (var data of dbinfo) {
        data = data.replace("(", "[");
        data = data.replace(")", "]");
        data = JSON.parse(data)
        // data is now array, append to tmp
        tmpArray.push(data)
    }

    dbinfo = tmpArray;

    // DBINFO in this instance is an array of base64 strings that are the maps we use in this monitor
    // CAMARRAY is how they are all associated

    // Doc Init
    var monitorbody = document.getElementById("monitorbody");
    // // CSS for making monitor look right.
    var body = document.body;
    body.style.margin = '0';
    body.style.padding = '0';
    body.style.overflow = 'hidden';
    body.style.backgroundColor = 'black';
    monitorbody.style.display = 'grid';
    // // Define columns and rows
    monitorbody.style.gridTemplateColumns = (`1fr`);
    monitorbody.style.gridTemplateRows = (`1fr`);
    // // Use full tab view
    monitorbody.style.height = '100vh';
    monitorbody.style.width = '100vw';
    // Single video element as background
    
    var templateDiv = document.createElement('div')
    var templateVideo = document.createElement('video')
    
    // CSS and attributes
    templateVideo.style.width = '100%';
    templateVideo.style.height = '100%';
    templateVideo.muted = true;
    templateVideo.disablePictureInPicture = true;
    templateVideo.autoplay = true;
    templateVideo.style.objectFit = 'contain';
    
    // Append the video to the div
    templateDiv.appendChild(templateVideo)
    
    // Set video and div ID
    templateVideo.id = "videoElement";
    templateDiv.id = "videoDiv";
    
    // Append div to main body
    monitorbody.appendChild(templateDiv)
    
    // Video elements created, now create map elements on loop based on floorArrays of camarray
    // First create div that will hold map

    var mapHoldDiv = document.createElement('div');
    
    mapHoldDiv.style.width = '600px';
    mapHoldDiv.style.height = '300px';
    mapHoldDiv.style.position = 'fixed';
    // Color for debug
    mapHoldDiv.style.backgroundColor = 'gray';
    mapHoldDiv.style.zIndex = '1000';
    mapHoldDiv.style.bottom = '0';
    mapHoldDiv.style.right = '0';
    mapHoldDiv.style.transform = 'translate(-15px, -95px)';
    mapHoldDiv.style.opacity = '50%'
    mapHoldDiv.style.overflow = 'hidden';
    mapHoldDiv.id = 'mapHoldDiv'
    
    monitorbody.appendChild(mapHoldDiv);

    // Below mapHoldDiv will be mapSelectDiv
    var mapSelectDiv = document.createElement('div');
    
    mapSelectDiv.style.width = '600px';
    mapSelectDiv.style.height = '60px';
    mapSelectDiv.style.position = 'fixed';
    // Color for debug
    // mapSelectDiv.style.backgroundColor = 'red';
    mapSelectDiv.style.zIndex = '1000';
    mapSelectDiv.style.bottom = '0';
    mapSelectDiv.style.right = '0';
    mapSelectDiv.style.transform = 'translate(-15px, -15px)';
    mapSelectDiv.style.opacity = '50%'

    // Left and right select buttons for 'scrolling' through available floors

    // LEFT
    var leftMapButton = document.createElement('div');
    leftMapButton.style.width = '40px';
    leftMapButton.style.height = '40px';
    leftMapButton.style.position = 'fixed';
    leftMapButton.style.backgroundColor = 'grey';
    leftMapButton.style.zIndex = '1000'
    leftMapButton.style.bottom = '0';
    leftMapButton.style.right = '0';
    leftMapButton.style.transform = 'translate(-550px, -10px)';
    leftMapButton.style.opacity = '50%'
    leftMapButton.style.justifyContent = "center";
    leftMapButton.style.alignItems = "center"; 
    leftMapButton.style.textAlign = "center";
    leftMapButton.style.fontSize = '25px';
    leftMapButton.style.fontWeight = 'bold';
    leftMapButton.style.userSelect = 'none';
    leftMapButton.style.cursor = "pointer";
    leftMapButton.textContent = '←';
    leftMapButton.addEventListener("click", function() {
        changeFloorMap('left');
    });

    mapSelectDiv.appendChild(leftMapButton);

    // RIGHT
    var rightMapButton = document.createElement('div');
    rightMapButton.style.width = '40px';
    rightMapButton.style.height = '40px';
    rightMapButton.style.position = 'fixed';
    rightMapButton.style.backgroundColor = 'grey';
    rightMapButton.style.zIndex = '1000'
    rightMapButton.style.bottom = '0';
    rightMapButton.style.right = '0';
    rightMapButton.style.transform = 'translate(-10px, -10px)';
    rightMapButton.style.opacity = '50%'
    rightMapButton.style.justifyContent = "center";
    rightMapButton.style.alignItems = "center"; 
    rightMapButton.style.textAlign = "center";
    rightMapButton.style.fontSize = '25px';
    rightMapButton.style.fontWeight = 'bold';
    rightMapButton.style.userSelect = 'none';
    rightMapButton.style.cursor = "pointer";
    rightMapButton.textContent = '→';
    rightMapButton.addEventListener("click", function() {
        changeFloorMap('right');
    });

    mapSelectDiv.appendChild(rightMapButton);

    // Third div in middle, shows current floor name
    var centerFloorText = document.createElement('div');
    centerFloorText.style.width = '200px';
    centerFloorText.style.height = '40px';
    centerFloorText.style.position = 'fixed';
    centerFloorText.style.backgroundColor = 'grey';
    centerFloorText.style.zIndex = '1000'
    centerFloorText.style.bottom = '0';
    centerFloorText.style.right = '0';
    centerFloorText.style.transform = 'translate(-180px, -10px)';
    centerFloorText.style.opacity = '100%'
    centerFloorText.style.justifyContent = "center";
    centerFloorText.style.alignItems = "center"; 
    centerFloorText.style.textAlign = "center";
    centerFloorText.style.fontSize = '25px';
    centerFloorText.style.fontWeight = 'bold';
    centerFloorText.style.userSelect = 'none';
    centerFloorText.textContent = 'FloorName';
    centerFloorText.id = 'centerFloorText';
    mapSelectDiv.appendChild(centerFloorText);
    
    // Append select div
    monitorbody.appendChild(mapSelectDiv);

    // For every floorArray in camarray, create a new map that can be selected with arrows
    
    var floorIndex = 0;
    for (var floorArray of camarray) {
        // Interperate floorArray as array object
        floorArray = JSON.parse(floorArray);
        
        // Set floor params
        var floorName = floorArray[0];
        var floorMap = floorArray[1];

        // Next objects in array are buttons, focus on drawing map first

        // Start with creating new div to hold all floorData, then like tabs, JS can choose to show one at a time, all the rest will be there
        // but not be interactable, or exist.

        var thisFloorDiv = document.createElement('div');
        // Set id based on array index
        thisFloorDiv.id = 'floorDiv:' + floorIndex;

        // Set image for div based on map

        var mapImageElement = document.createElement('img');
        mapImageElement.style.bottom = '0';
        mapImageElement.style.width = '600px';
        mapImageElement.style.position = 'absolute';

        for (var mapData of dbinfo) {
            // Does this mapName = floorMap
            if (floorMap == mapData[0]) {
                // Found match! Set image source
                mapImageElement.src = ('data:image/png;base64,' + mapData[1]);
            }
        }
                
        thisFloorDiv.appendChild(mapImageElement);

        // Create buttons under thisFloorDiv so that they are contained
        // Loop over every available buttonArray for this current floor

        var buttonTrack = 0;

        for (var buttonArray of floorArray) {
            // Ignore first two indexes

            if (buttonTrack < 2) {
                buttonTrack++;
            }
            // buttonTrack is above 2, can process data now
            else {
                // Create button based on buttonTrack - 2

                let newButton = document.createElement('div');
                newButton.style.display = 'inline-block';
                newButton.style.border = '1px solid #000';
                newButton.style.backgroundColor = '#dedede';
                newButton.style.padding = '5px 10px';
                newButton.style.cursor = 'pointer';
                newButton.style.position = 'fixed';
                newButton.style.textAlign = 'center';
                newButton.style.zIndex = '1005';
                newButton.id = 'cambutton';
                newButton.textContent = 'Cam ' + (buttonTrack - 1);

                thisFloorDiv.appendChild(newButton);

                // Change position based on mapHoldDiv

                // PercentAndPixel equation variables
                var mapHoldDiv = document.getElementById('mapHoldDiv');
                // Top left of mapEditDiv
                var mapHoldDivXOrigin = mapHoldDiv.offsetLeft;
                var mapHoldDivYOrigin = mapHoldDiv.offsetTop;
                // Bottom right of mapEditDiv
                var mapHoldDivHeightAbsolute = (mapHoldDivYOrigin + mapHoldDiv.offsetHeight);
                var mapHoldDivWidthAbsolute = (mapHoldDivXOrigin + mapHoldDiv.offsetWidth);
                // Existing data to grab from array
                var percentX = buttonArray[1];
                var percentY = buttonArray[2];
                
                // Calculate pixel position for button
                var buttonOffsetLeft = (percentX / 100) * (mapHoldDivWidthAbsolute - mapHoldDivXOrigin) + mapHoldDivXOrigin;
                var buttonoffsetTop = (percentY / 100) * (mapHoldDivHeightAbsolute - mapHoldDivYOrigin) + mapHoldDivYOrigin;

                // Set calculated button position (IS NOT CURRENTLY ACCURITE, not sure why)
                newButton.style.left = ((buttonOffsetLeft - mapHoldDivXOrigin)) + 'px';
                newButton.style.top = ((buttonoffsetTop - mapHoldDivYOrigin) + 35) + 'px';

                // Set action on click

                let camname = buttonArray[0];

                newButton.addEventListener("click", function() {
                    changeActiveCameraByName(camname);
                });

                // If this camera name is unique, add to camNameArray to pass to webRTC get streams so we get no duplicate streams
                // Makes it easy to select camera based on name to, just lookup position in array

                var isInArray = false;

                for (var cam of camNameArray) {
                    if (cam == camname) {
                        isInArray = true;
                    }
                }

                if (isInArray == false) {
                    camNameArray.push(camname);
                }

                // End of button logic
                buttonTrack++;   
            }
        }


        // Floor and button creation done, append to mapHoldDiv
        thisFloorDiv.style.display = 'none';
        mapHoldDiv.appendChild(thisFloorDiv);

        // By default, show floorDiv:0
        var floorDiv = document.getElementById('floorDiv:0');
        floorDiv.style.display = 'block';

        // Set height of mapHoldDiv based on floorDiv img
        var wantedHeight = floorDiv.querySelector('img').height;
        mapHoldDiv.style.height = wantedHeight + 'px';

        // Increase floorIndex
        floorIndex++;
    }

    // Floors created, set default to floor 0, first camera in array will be selected

    // Set current map text

    // Grab first floor, name
    var firstFloor = camarray[0]
    firstFloor = JSON.parse(firstFloor);
    centerFloorText.textContent = (firstFloor)[0];
        
    // When all elements created, start webrtc
    startWebRtcStreamsAndAttatch(camNameArray);
}