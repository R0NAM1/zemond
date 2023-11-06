import '/static/node_modules/webrtc-adapter/out/adapter.js';
import { stunServer } from '/static/js/stunServer.js';
// Adapter JS takes over certain functions if needed, for browser cross-compatability.
// You just include it and it does the rest.
// Import Stun Server URL from seperate JS file

// Variables used across the file
var pc = null, dcInterval = null;
var videoTrackArray = [];
var currentSlideIndex = 0;
var currentCamIndex = 0;

// In this file, get all relevent information, and either draw a single video frame taking up the whole display. or the same as xbx mon
// After X amount of time, redraw screen with next information

// Simple sleep function, blocks thread
// Use in while loop so we don't run it 8192 times a second, rather every x seconds.
function sleepForMiliseconds(miliseconds) {
    return new Promise(resolve => setTimeout(resolve, miliseconds));
}

// Generate SDP and send to server monitor offers
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
        var sess = new RTCSessionDescription(answer) // Set Session Description Object to Server Answer
        return pc.setRemoteDescription(sess);   //Finally, set the remote peers description.
    })
}


// Start webrtc streams and put them all in an array to grab whenever requested
function startWebRtcStreamsAndAttatch(camarray) {
    console.log("Detected Browser As: " + adapter.browserDetails.browser + " " + adapter.browserDetails.version)
    var config = {
        sdpSemantics: 'unified-plan', // Modern SDP format.
        iceServers: [stunServer]
    };

    pc = new RTCPeerConnection(config); // Set server to config

    // When we get a track from the server
    pc.addEventListener('track', function(evt) {
        if (evt.track.kind == 'video') {
            // Put mediastream into array
            let incomingStream = new MediaStream([evt.track]);
        
            // Add track to array, so it can be accessed when requested
            videoTrackArray.push(incomingStream);
        }
    });

    // Define datachannel object and global pc and dc object
    let dc = pc.createDataChannel('chat');
    let globalPcObject = pc;
    let globalDcObject = dc;
    // Closing case
    dc.onclose = function() {
        clearInterval(dcInterval);
        dataChannelLog.textContent += '- close\n';
    };
    dc.onopen = function() {
        // Set interval to ping every second, heartbeat
        dcInterval = setInterval(function() {
            var message = 'ping';
            dc.send(message);
        }, 1000);
    };

    // Loop over for all camarray entries and add transceiver for each
    for (let i = 0; i < (camarray).length; i++) {
        pc.addTransceiver('video', {direction: 'recvonly'}); // We only receive video
    }

    // Negotiate clients and connect peers
    negotiate(); 
}

// Have seperate functions for redrawing
// Redraw screen to a single 1x1 video that shows our wanted camera.
function redrawToCamera(camera) {
    var monitorbody = document.getElementById("monitorbody");

    // Reset to blank slate
    while (monitorbody.firstChild) {
        monitorbody.firstChild.remove();
    }
    
    // CSS for making monitor look right.
    var body = document.body;
    body.style.margin = '0';
    body.style.padding = '0';
    body.style.overflow = 'hidden';
    body.style.backgroundColor = 'black';
    monitorbody.style.display = 'grid';
    // // Define columns and rows
    monitorbody.style.gridTemplateColumns = (`repeat(1, 1fr)`);
    monitorbody.style.gridTemplateRows = (`repeat(1, 1fr)`);
    // // Use full tab view
    monitorbody.style.height = '100vh';
    monitorbody.style.width = '100vw';
       
    // Template Elements
    var templateDiv = document.createElement('div');
    var templateVideo = document.createElement('video');

    // CSS and attributes
    templateVideo.style.width = '100%';
    templateVideo.style.height = '100%';
    templateVideo.muted = true;
    templateVideo.disablePictureInPicture = true;
    templateVideo.autoplay = true;
    templateVideo.style.objectFit = 'contain';
        
    // Append the video to the div
    templateDiv.appendChild(templateVideo);
    
    // Append div to main body
    monitorbody.appendChild(templateDiv);

    // First grab current videoTrackArray object, then set templateVideo
    templateVideo.srcObject = videoTrackArray[currentCamIndex];
    // Single monitor is now drawn.
    // Advance index
    currentCamIndex += 1;
}

// Implementation of XbX view in a single function, draws the amount from lxw and uses that amount to grab cameras
// from videoStreamArray
// (Did observe odd indexing bug with one test monitor, cannot recreate unless with that monitor and couldn't figure out what was
// indexing wrong, it almost skipped one, or went back one and looped before, but it was mostly correct from endOfIndex to about the middle)
function redrawToMonitor(lxw, camarray) {
    var monitorbody = document.getElementById("monitorbody");
    
    // Reset to blank slate
    while (monitorbody.firstChild) {
        monitorbody.firstChild.remove();
    }
    
    // Calculate amount of cameras to advance index from
    var camamount = (lxw[0] * lxw[1]);

    // // CSS for making monitor look right.
    var body = document.body;
    body.style.margin = '0';
    body.style.padding = '0';
    body.style.overflow = 'hidden';
    body.style.backgroundColor = 'black';
    monitorbody.style.display = 'grid';
    // // Define columns and rows
    monitorbody.style.gridTemplateColumns = (`repeat(${lxw[1]}, 1fr)`);
    monitorbody.style.gridTemplateRows = (`repeat(${lxw[0]}, 1fr)`);
    // // Use full tab view
    monitorbody.style.height = '100vh';
    monitorbody.style.width = '100vw';
    
    // // Create DIVS and video elements based on camamount, on creation grab from index and assign element
    for (let i = 0; i < camamount; i++) {
        // Template Elements
        var templateDiv = document.createElement('div');
        var templateVideo = document.createElement('video');

        // CSS and attributes
        templateVideo.style.width = '100%';
        templateVideo.style.height = '100%';
        templateVideo.muted = true;
        templateVideo.disablePictureInPicture = true;
        templateVideo.autoplay = true;
        templateVideo.style.objectFit = 'contain';
        
        // Append the video to the div
        templateDiv.appendChild(templateVideo);
 

        // Assign stream to video
        templateVideo.srcObject = videoTrackArray[currentCamIndex];
        // Advance this index by one
        currentCamIndex += 1;
        // Append div to main body
        monitorbody.appendChild(templateDiv);
    }
}

// Forever looping function that waits for x seconds before advancing slide
async function slideShowAdvanceAutomatic(dbinfo, camarray, videoTrackArray) {
    // Run forever
    while (true) {
        // Delta is time until we advance to next slide
        var delta = window.delta;

        // Video track array is our sources
        // dbinfo tells us if it's a single camera or monitor
        // camarray is a list of all cameras in order, we can track which one to grab by either grabbing single, of calculating xbx and pulling
        // that many

        // Read current index, determine if camera or monitor, and draw accordingly

        if (dbinfo[currentSlideIndex] == 'single') {
            // Is a single camera, draw as such
            redrawToCamera(camarray[currentCamIndex]);
        }
        else {
            // Not a single camera, so must be a monitor!
            // Process lxw xbx from db
            var xbx = dbinfo[currentSlideIndex];
            xbx = xbx.split("x");
            //Draw with sending number of cams, internally loops camindex so each cam is draw as it should be, advancing index by 1 each time
            redrawToMonitor(xbx, camarray);
        }


        // Wait for deltatime, multiple by 1000 to make milliseonc compatable
        await sleepForMiliseconds((delta * 1000))
        // Advance to next index! 
        
        // If our index goes above the length of our array, reset to 0
        if (currentSlideIndex >= (dbinfo.length - 1)) {
            currentSlideIndex = 0
        }
        else{
            // If not overflowing, advance index so next loop can grab this instead
            currentSlideIndex += 1;
        }
        // Reset if camarray overflows
        if (currentCamIndex >= (camarray.length)) {
            currentCamIndex = 0
        }
        // Loops here!
    }
}

// Initial function that runs on monitor window.load, REQUIRED!
export async function loadMonitor() {
    // Processing on data from server and db, fixing encoding issues etc etc
    var dbinfo = (window.dbinfo).replace(/&#39;/g, "");
    dbinfo = (dbinfo).replace(/&#34;/g, "");
    var camarray = String((window.camarray).replace(/&#39;/g, '"'));

    // Convert camarray string back to native array (No I don't know why JSON.parse can do that)
    camarray = JSON.parse(camarray)
    
    // Split DB info into array
    dbinfo = (dbinfo.substring(1, dbinfo.length - 1)).split(", ");

    // With data now, we start running slideshowStart
    // slideshow start reading dbinfo, to see if it's a single cam, if so redraw to that
    // if not, assume monitor and draw that.

    // First, start webrtc stream, even if not drawing to screen
    startWebRtcStreamsAndAttatch(camarray);

    // Now we have all streams coming to the client, accessable in videoTrackArray
    // Wait for it to be filled until we continue

    while (camarray.length > videoTrackArray.length) {
        // console.log("waiting for all tracks...")
        await sleepForMiliseconds(2000);
    }

    // Can only get here when while loop breaks, must have all tracks!

    // Debug lines
    // console.log(videoTrackArray)
    // console.log(dbinfo)
    // console.log(camarray)

    // Start forever loop to advance slides
    slideShowAdvanceAutomatic(dbinfo, camarray, videoTrackArray)
}