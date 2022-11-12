import '/static/node_modules/webrtc-adapter/out/adapter.js';
// Adapter JS takes over certain functions if needed, for browser cross-compatability.
// You just include it and it does the rest.
var pc = null;
// PC Will Be The Server
let stream = new MediaStream();
// Stream is whatever we get from the server
var dc = null, dcInterval = null;
// Data Channel


// This Function runs asycnronously, calls adapter.js to get the browser type and version, then creates an offer based on some
// config to send to the server.
async function negotiate() {
    console.log("Detected Browser As: " + adapter.browserDetails.browser + " " + adapter.browserDetails.version)
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
        var offer = pc.localDescription; // Send our offer to the server in a JSON format, we expect a raw ANSWER, not encapsulated,
        return fetch('/rtcoffer/' + cameraName, {
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
        var sess = new RTCSessionDescription(answer) // Set the response to our answer.
        return pc.setRemoteDescription(sess);   //Finally, set the remote peers description.
    })
}

    // Start WebRTC
export function start() {
    var config = {
        sdpSemantics: 'unified-plan', // Modern SDP format.
        iceServers: [{"urls": "stun:nvr.internal.my.domain"}] //This will be dynamic based on server config later
    };

    pc = new RTCPeerConnection(config); // Set server to config



    // connect audio / video
    pc.addEventListener('track', function(evt) {
        if (evt.track.kind == 'video') {
            document.getElementById('video').srcObject = evt.streams[0]; // 'Video' includes audio as a substream
        }
    });

    //For Ice troubleshooting
    // pc.addEventListener('iceconnectionstatechange', function(evt) {
    //     console.log("ICE Connection is: " + pc.connectionState)
    //     console.log("ICE Remote Description is: " + pc.currentRemoteDescription)
    // });

    // Add Data Channels For PingPong

    dc = pc.createDataChannel('chat') 
    dc.onclose = function() {
        clearInterval(dcInterval);
        dataChannelLog.textContent += '- close\n';
    };
    dc.onopen = function() {
        dcInterval = setInterval(function() {
            var message = 'ping';
            console.log("Ping!");
            dc.send(message);
        }, 1000);
    };
    dc.onmessage = function(evt) {

        if (evt.data.substring(0, 4) === 'pong') {
            console.log("Pong!");
        }
    };

    pc.addTransceiver('video', {direction: 'recvonly'}); // We only receive video
    pc.addTransceiver('audio', {direction: 'recvonly'}); // We only receive audio

    negotiate(); // Negotiate clients and connect peers

    
}

export function stop() { // Close Peer, if wanted.

    // close peer connection
    setTimeout(function() {
        pc.close();
    }, 500);
}

window.onload = start() // When webpage is done loading, run the 'start()' function.