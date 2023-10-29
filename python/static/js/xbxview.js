import '/static/node_modules/webrtc-adapter/out/adapter.js';
import { stunServer } from '/static/js/stunServer.js';
// Adapter JS takes over certain functions if needed, for browser cross-compatability.
// You just include it and it does the rest.
// Import Stun Server URL from seperate JS file

var pc = null, dcInterval = null;

// In this file, create the elements from the db by taking the lxw, multiplying a div that contains a video element that connects to any video that way said.
// Then run modified webrtc connection script, for now just make text elements

async function negotiate() {
    // Send offer to server for WebRTC
    return pc.createOffer({iceRestart:true}).then(function(offer) {

        // Forcefully change the SDP pref from Vp8 to H264

        // offer.sdp = offer.sdp.replaceAll('VP9', 'H264')

        // Remove other lines
        // let splitSdp = offer.sdp.split('\r\n');

        // // Store track ID to remove from m=video
        // let trackIdStore = []

        // for (let i = 0; i < splitSdp.length; i++) {
        //     if (splitSdp[i].includes('a=rtpmap') && splitSdp[i].includes('VP8')) {
        //         //Grab Id
        //         let id = splitSdp[i].split(":")
        //         id = id[1].split(' ')[0]
        //         trackIdStore.push(id)

        //         // splitSdp.splice(i, 1);
        //         // i--;
        //     }
        //     else if (splitSdp[i].includes('a=rtpmap') && splitSdp[i].includes('rtx')) {
        //         //Grab Id
        //         let id = splitSdp[i].split(":")
        //         id = id[1].split(' ')[0]
        //         trackIdStore.push(id)
                
        //         splitSdp.splice(i, 1);
        //         i--;
        //     }
        // }

        // // Find m=video in splitSdp and remove IDS

        // for (let i = 0; i < splitSdp.length; i++) {
        //     if (splitSdp[i].includes('m=video')) {
        //         console.log("Before:")
        //         console.log(splitSdp[i])
        //         for (let id of trackIdStore) {
        //             console.log("Replacing track ID " + id)
        //             splitSdp[i] = splitSdp[i].replace(id, "")
        //         }
        //         console.log("After:")
        //         console.log(splitSdp[i])
        //     }
        
        // }

        // offer.sdp = splitSdp.join('\r\n')

        // offer.sdp = offer.sdp.replaceAll('VP8', 'H264')
        // offer.sdp = offer.sdp.replaceAll('VP8', 'H264')


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


// Autorun once video columms are created.
function startWebRtcStreamsAndAttatch(lxw, camarray) {
    console.log("Detected Browser As: " + adapter.browserDetails.browser + " " + adapter.browserDetails.version)
    var config = {
        sdpSemantics: 'unified-plan', // Modern SDP format.
        iceServers: [stunServer] //This will be dynamic based on server config later
    };

    pc = new RTCPeerConnection(config); // Set server to config

    // Start at cam 1, will go up per track added.
    let currentCam = 1;

    // Connect audio and video to each wanted element
    pc.addEventListener('track', function(evt) {
        // Only called when a track is added, should happen per transceiver.
        if (evt.track.kind == 'video') {
            // Should get incoming track here, make it it's own object, cannot use embedded streams[0] object.
            let incomingStream = new MediaStream([evt.track]);
        
            // Set current cam ID to incomingStream
            document.getElementById((currentCam) + ":video").srcObject = incomingStream;
            
            // Next camera
            currentCam++;
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

    // Loop over for all video elements so I can recieve each track from each transciever.
    for (let i = 0; i < Object.keys(camarray).length; i++) {
        console.log("Adding Transceivers for: " + (i+1) + ": " + Object.keys(camarray[String(i+1)]))
        pc.addTransceiver('video', {direction: 'recvonly'}); // We only receive video
        pc.addTransceiver('audio', {direction: 'recvonly'}); // We only receive audio
    }

    // Negotiate clients and connect peers
    negotiate(); 
}

export function loadMonitor() {
    // Add all video elements and assign IDS for WebRTC array.
    // Replace " with nothing or ".
    var dbinfo = (window.dbinfo).replace(/&#39;/g, "")
    var camarray = String((window.camarray).replace(/&#39;/g, '"'))

    // Split DB info into array, and trim camarray
    dbinfo = (dbinfo.substring(1, dbinfo.length - 1)).split(", ")
    camarray = camarray.substring(1, camarray.length - 2)

    // Split Length x Width
    var lxw = dbinfo[0].split("x")

    // Get final camera amount from lxw
    var camamount = (lxw[0] * lxw[1])

    // Parse DB entry into JSON camarray
    camarray = JSON.parse(camarray)

    // Data parsed
    // For the amount of cameras, create as many elements.

    var monitorbody = document.getElementById("monitorbody");
    // CSS for making monitor look right.
    var body = document.body;
    body.style.margin = '0';
    body.style.padding = '0';
    body.style.overflow = 'hidden';
    body.style.backgroundColor = 'black';
    monitorbody.style.display = 'grid';
    // Define columns and rows
    monitorbody.style.gridTemplateColumns = (`repeat(${lxw[1]}, 1fr)`);
    monitorbody.style.gridTemplateRows = (`repeat(${lxw[0]}, 1fr)`);
    // Use full tab view
    monitorbody.style.height = '100vh';
    monitorbody.style.width = '100vw';
    
    // Create DIVS and video elements based on camamount, assign unique IDS
    for (let i = 0; i < camamount; i++) {
        
        // Template Elements
        var templateDiv = document.createElement('div')
        var templateVideo = document.createElement('video')

        // CSS and attributes
        templateVideo.style.width = '100%';
        templateVideo.style.height = '100%';
        templateVideo.muted = true;
        templateVideo.poster = '/static/pictures/logo.png';
        templateVideo.autoplay = true;
        templateVideo.style.objectFit = 'contain';
        
        // Append the video to the div
        templateDiv.appendChild(templateVideo)
 
        // Set current camera name
        var camera = Object.keys(camarray[String(i+1)])
        
        // Set video and div ID
        templateVideo.id = (i + 1) + ":video";
        templateDiv.id = (i + 1) + ":" + camera[0];

        // Append div to main body
        monitorbody.appendChild(templateDiv)
    }

    // When all elements created, start webrtc
    startWebRtcStreamsAndAttatch(lxw, camarray);
}