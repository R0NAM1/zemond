import '/static/node_modules/webrtc-adapter/out/adapter.js';
// Adapter JS takes over certain functions if needed, for browser cross-compatability.
// You just include it and it does the rest.
var pc = null;
// PC Will Be The Server
let stream = new MediaStream();
// Stream is whatever we get from the server
var dc = null, dcInterval = null, globalDcObject = null;

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
    globalDcObject = dc;
    dc.onclose = function() {
        clearInterval(dcInterval);
        dataChannelLog.textContent += '- close\n';
    };
    dc.onopen = function() {
        dcInterval = setInterval(function() {
            var message = 'ping';
            // console.log("Ping!");
            dc.send(message);
        }, 1000);
    };
    dc.onmessage = function(evt) {

    // console.log(evt.data);

    let lcData = (evt.data).toString();

    // When we receive data, process it here. Mainly just updating variables.

        // Second check if message is a valid data type, valid types are defined below in webrtc_var_data_types

        const webrtc_var_data_types = ["ptzcoordupdate|"];

        // Depending on type, update variable

            // So, in the context of your code, (type => lcData.includes(type)) is a function that checks if lcData includes the current element in the webrtc_var_data_types array. If it does, the function returns true, and findIndex() returns the index of that element javascript.info.
            // https://www.phind.com/agent?cache=clkvplmrt0007mm085y9pwizb
        
        let webrtc_var_data_types_index_return = webrtc_var_data_types.findIndex(type => lcData.includes(type));
        // -1 if not valid message.

        let message_type = (webrtc_var_data_types.toString(webrtc_var_data_types_index_return));

        // Now message type is valid, extract data

        if (webrtc_var_data_types_index_return >= 0) {
            let webrtc_data = lcData.split("|")
            // console.log(webrtc_data[1])
        
            switch(message_type) {

                case 'ptzcoordupdate|':

                    document.getElementById('xyzcoordtext').innerHTML = "XYZ Coords: " + webrtc_data[1]
            }}


    };

    pc.addTransceiver('video', {direction: 'recvonly'}); // We only receive video
    pc.addTransceiver('audio', {direction: 'recvonly'}); // We only receive audio

    negotiate(); // Negotiate clients and connect peers

    
}

export function sendPtzMessage(direction) {

    if (direction == 'up') {
        globalDcObject.send("up")
    }
    else if (direction == 'down') {
        globalDcObject.send("down")
    }
    else if (direction == 'left') {
        globalDcObject.send("left")
    }
    else if (direction == 'right') {
        globalDcObject.send("right")
    }
    else if (direction == 'positive') {
        globalDcObject.send("positive")
    }
    else if (direction == 'negative') {
        globalDcObject.send("negative")
    }
    else if (direction == 'stop') {
        globalDcObject.send("stop")
    }
}

export function stop() { // Close Peer, if wanted.

    // close peer connection
    setTimeout(function() {
        pc.close();
    }, 500);
}

window.onload = start() // When webpage is done loading, run the 'start()' function.