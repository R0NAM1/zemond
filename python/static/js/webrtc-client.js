import '/static/node_modules/webrtc-adapter/out/adapter.js';
import { stunServer } from '/static/js/stunServer.js';
// Adapter JS takes over certain functions if needed, for browser cross-compatability.
// You just include it and it does the rest.
// Import Stun Server URL from seperate JS file
var pc = null;

// PC Will Be The Server
let stream = new MediaStream();
let outputStream;

// Stream is whatever we get from the server
var dc = null, dcInterval = null, globalDcObject = null, globalPcObject = null, micTrack = null, finalTrack = null, hasCameraControl = false, hasTWA = false, hasPTZ = false, gpButton = false;
var hasMicControl = false;

// Game pad loop to check buttons, runs async to always check
async function gamepadLoopCheck() {
    var gamepads = navigator.getGamepads();
    var gamepad = gamepads[0];

    // If Permission is granted:
    if (hasPTZ && hasCameraControl) {
    // If I get a gamepad
        if (gpButton == false) {
            // DPAD UP (Axis 7: -1)
            // DPAD DOWN (Axis 7: 1)
            // DPAD LEFT (Axis 6: -1)
            // DPAD RIGHT (Axis 6: 1)
            // DPAD left up (Axis 1: -1)
            // DPAD left down (Axis 1: 1)
            
            if (gamepad.axes[1] > 0.75) {
                // console.log("-");
                sendPtzMessage('negative', speedSlider.value)
                gpButton = true;
            }
            else if (gamepad.axes[1] < -0.75) {
                // console.log("+");
                sendPtzMessage('positive', speedSlider.value)
                gpButton = true;
            }
            else if (gamepad.axes[6] == 1) {
                // console.log("Right");
                sendPtzMessage('right', speedSlider.value)
                gpButton = true;

            }else if (gamepad.axes[6] == -1) {
                // console.log("Left");
                sendPtzMessage('left', speedSlider.value)
                gpButton = true;

            }else if (gamepad.axes[7] == 1) {
                // console.log("Down");
                sendPtzMessage('down', speedSlider.value)
                gpButton = true;

            }else if (gamepad.axes[7] == -1) {
                // console.log("Up")
                sendPtzMessage('up', speedSlider.value)
                gpButton = true;
            }
        }
        else if (gpButton == true) {
            // Check if I'm still pressing buttons
            if (gamepad.axes[1] < 0.75 && gamepad.axes[1] > -0.75 && gamepad.axes[6] == 0 && gamepad.axes[7] == 0) {
                gpButton = false;
                console.log("Not pressing a button")
                sendPtzMessage('stop');
            }
           
        }
    }
}
 // Axis check (Uncomment to show debug for axes)
            // for (var i = 0; i < gamepad.axes.length; i++) {
            //     var axis = gamepad.axes[i];
            //     console.log("Axis " + i + ": value = " + axis);
            //   }

// For arrow key ptz control
function arrowKeyCheckAddListeners() {

    // If key up is certain key, send stop
    document.addEventListener('keyup', (event) => {

        if (event.key === 'ArrowUp' || event.key === 'ArrowDown' || event.key === 'ArrowLeft' || event.key === 'ArrowRight' || event.key === '+' || event.key === '-') {
            gpButton = false;
            sendPtzMessage('stop')
        }

    })

    // On key down
    document.addEventListener('keydown', (event) => {
        // If Can and has Permission
        if (hasPTZ && hasCameraControl) {
            // If current button is false
            if(gpButton == false) {
                // If Shift Key, divide speed.
                // If Any Valid key, send movement
                var divideSpeed = false;

                if (event.shiftKey) {
                    divideSpeed = true;
                }

                if (event.key === 'ArrowUp') {
                    if (divideSpeed) {
                        sendPtzMessage('up', (speedSlider.value/2.5))
                    }
                    else{
                        sendPtzMessage('up', speedSlider.value)
                    }
                    
                    gpButton = true;
                }
                else if (event.key === 'ArrowDown') {
                    if (divideSpeed) {
                        sendPtzMessage('down', (speedSlider.value/2.5))
                    }
                    else{
                        sendPtzMessage('down', speedSlider.value)
                    }
                    
                    gpButton = true;
                }
                else if (event.key === 'ArrowLeft') {
                    if (divideSpeed) {
                        sendPtzMessage('left', (speedSlider.value/2.5))
                    }
                    else{
                        sendPtzMessage('left', speedSlider.value)
                    }
                    
                    gpButton = true;
                }
                else if (event.key === 'ArrowRight') {
                    if (divideSpeed) {
                        sendPtzMessage('right', (speedSlider.value/2.5))
                    }
                    else{
                        sendPtzMessage('right', speedSlider.value)
                    }
                    
                    gpButton = true;
                }
                else if (event.key === '+') {
                    if (divideSpeed) {
                        sendPtzMessage('positive', (speedSlider.value/2.5))
                    }
                    else{
                        sendPtzMessage('positive', speedSlider.value)
                    }
                    
                    gpButton = true;
                }
                else if (event.key === '-') {
                    if (divideSpeed) {
                        sendPtzMessage('negative', (speedSlider.value/2.5))
                    }
                    else{
                        sendPtzMessage('negative', speedSlider.value)
                    }
                    
                    gpButton = true;
                }
                
        }
    }})


}

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
export async function startWebRtc(resampledMicTrack) {
    var config = {
        sdpSemantics: 'unified-plan', // Modern SDP format.
        iceServers: [stunServer] //This will be dynamic based on server config later
    };

    pc = new RTCPeerConnection(config); // Set server to config

    // connect audio / video
    // + audio backstream for 'two way audio'
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
    globalPcObject = pc;
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

        const webrtc_var_data_types = ["ptzcoordupdate|", "truetwa", "controlallow", "controldeny", "controlbreak"];

        // Depending on type, update variable

            // So, in the context of your code, (type => lcData.includes(type)) is a function that checks if lcData includes the current element in the webrtc_var_data_types array. If it does, the function returns true, and findIndex() returns the index of that element javascript.info.
            // https://www.phind.com/agent?cache=clkvplmrt0007mm085y9pwizb
        
        let webrtc_var_data_types_index_return = webrtc_var_data_types.findIndex(type => lcData.includes(type));
        // -1 if not valid message.

        let message_type = (webrtc_var_data_types[webrtc_var_data_types_index_return]);

        // Now message type is valid, extract data

        if (webrtc_var_data_types_index_return >= 0) {
            let webrtc_data = lcData.split("|")
            // console.log(webrtc_data[1])
            // console.log(message_type)
            // If valid message allow control allow
            document.getElementById('controlButton').style.opacity = "1.0"
            document.getElementById('controlButton').style.pointerEvents = "all"

            switch(message_type) {

                case 'ptzcoordupdate|':
                    hasPTZ = true;
                        document.getElementById('xyzcoordtext').innerHTML = "XYZ Coords: " + webrtc_data[1]
                    if (hasCameraControl == true) {
                        document.getElementById('xyzcoord').style.opacity = "1.0"
                        document.getElementById('xyzcoord').style.pointerEvents = "all"
                    } else {
                        document.getElementById('xyzcoord').style.opacity = "0.6"
                        document.getElementById('xyzcoord').style.pointerEvents = "none"
                    }
                        break;

                case 'truetwa':
                    hasTWA = true; 
                    break;

                case 'controlallow':
                    hasCameraControl = true;
                    document.getElementById('controlButton').value = "Relenquish Control"
                    document.getElementById('needControl').style.opacity = "1.0"
                    document.getElementById('needControl').style.pointerEvents = "all"
                    if (hasTWA) {
                        document.getElementById('twowayaudio').style.opacity = "1.0"
                        document.getElementById('twowayaudio').style.pointerEvents = "all"
                    }
                    break;

                case 'controldeny':
                    hasCameraControl = false;
                    document.getElementById('controlButton').value = "Control Denied"
                    document.getElementById('needControl').style.opacity = "0.6"
                    document.getElementById('needControl').style.pointerEvents = "none"
                    document.getElementById('xyzcoord').style.opacity = "0.6"
                    document.getElementById('xyzcoord').style.pointerEvents = "none"
                    if (hasTWA) {
                        document.getElementById('twowayaudio').style.opacity = "0.6"
                        document.getElementById('twowayaudio').style.pointerEvents = "none"
                    }
      
                    break;
                
                case 'controlbreak':
                    hasCameraControl = false;
                    document.getElementById('needControl').style.opacity = "0.6"
                    document.getElementById('needControl').style.pointerEvents = "none"
                    document.getElementById('xyzcoord').style.opacity = "0.6"
                    document.getElementById('xyzcoord').style.pointerEvents = "none"
                    if (hasTWA) {
                        document.getElementById('twowayaudio').style.opacity = "0.6"
                        document.getElementById('twowayaudio').style.pointerEvents = "none"
                    }
                    document.getElementById('controlButton').value = "Request Control"
                }
            }

    };

    pc.addTransceiver('video', {direction: 'recvonly'}); // We only receive video
    pc.addTransceiver('audio', {direction: 'sendrecv'}); // We send and receive audio

    // console.log(resampledMicTrack)
    if (hasMicControl == true) {
        globalPcObject.addTrack(resampledMicTrack);
    }

    negotiate(); // Negotiate clients and connect peers
}


export async function toggleTwoWayAudio() {

    if (micToggled == false) {
        // Set Button to toggled
        document.getElementById('microphonetogglebutton').style.backgroundColor = "darkgrey"

        globalDcObject.send("truetwa")

        micToggled = true
    }
    else if (micToggled == true) {
        globalDcObject.send("falsetwa")

        document.getElementById('microphonetogglebutton').style.backgroundColor = "lightgrey"

        micToggled = false
    }
}

export function sendPtzMessage(direction,speed) {

    if (direction == 'up') {
        globalDcObject.send("up:"+speed)
    }
    else if (direction == 'down') {
        globalDcObject.send("down:"+speed)
    }
    else if (direction == 'left') {
        globalDcObject.send("left:"+speed)
    }
    else if (direction == 'right') {
        globalDcObject.send("right:"+speed)
    }
    else if (direction == 'positive') {
        globalDcObject.send("positive:"+speed)
    }
    else if (direction == 'negative') {
        globalDcObject.send("negative:"+speed)
    }
    else if (direction == 'stop') {
        globalDcObject.send("stop")
    }
}

export function requestCameraControl() {
    // Send WebRTC Message and wait for either yay or nay from server
    globalDcObject.send("requestCameraControl")
}

export function stop() { // Close Peer, if wanted.
    // close peer connection
    setTimeout(function() {
        pc.close();
    }, 500);
}

export async function start() {
    // OK, I've spent at least a two weeks on grabbing the Microphone audio, pumping it into a resampler to get it to 8000 samples,
    // and then piped into the webrtc stream. Uding offline audio contexts, it SHOULD work.
    // That used to be the above idea, I just send the raw audio data now :[
    const myAudioContext = new AudioContext();

    document.getElementById('needMicModal').style.display = 'none';

    // Make video element pan and zoomable
    // var videoElement = document.getElementById('video')
    // window.panzoom(videoElement);
    // Works, but videoplayer needs to mature enough to be fancy with it


   // For fun, if a gamepad is detected, allow it to control the PTZ controls, but need to check if allowed from server.
   window.addEventListener('gamepadconnected', function(event) {
    var gamepad = event.gamepad;
    console.log('Gamepad connected: ' + gamepad.id);
    setInterval(gamepadLoopCheck, 100);
    });

    arrowKeyCheckAddListeners()

   // Put Mic into MediaStream
   try {
        const myMediaStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        // Put MediaStream into comptatable source
        const myMediaStreamSource = myAudioContext.createMediaStreamSource(myMediaStream)

        //    console.log("Context Sample Rate: " + myAudioContext.sampleRate)

        const myMediaStreamDestination = myAudioContext.createMediaStreamDestination();
        myMediaStreamSource.connect(myMediaStreamDestination)

        outputStream = myMediaStreamDestination.stream.getAudioTracks()[0];
        hasMicControl = true;
   
        startWebRtc(outputStream)
    }
    catch {
        startWebRtc()
    }

}

// window.onload = start(); // When webpage is done loading, run the 'startWebRtc()' function.
//Can't run automatically now as AudoContext cannot load without user input :/