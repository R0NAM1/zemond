import asyncio, ast, json, time, cryptocode, av, uuid, cv2, numpy, threading, os
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCDataChannel, RTCRtpCodecParameters
from aiortc.mediastreams import VideoFrame
from aiortc.contrib.media import MediaPlayer, MediaRelay, MediaBlackhole, MediaStreamTrack
from aiortc.rtcrtpsender import RTCRtpSender
from globalFunctions import passwordRandomKey, myCursor, myDatabase, sendONVIFRequest, userUUIDAssociations
from ptzHandler import updatePTZReadOut, sendAuthenticatedPTZContMov
from twoWayAudio import streamBufferToRemote
from webRtcObjects import CameraPlayer, CameraPlayerTrack, cameraPlayerDictionary

global userUUIDAssociations

## This file holds all the different ways to give out WebRTC

stunServer = 'stun:nvr.internal.my.domain'

def requestCameraPlayer(dockerIp):
    # Attempt to get existing
    try:
        cameraPlayer = cameraPlayerDictionary[dockerIp]
    except:
        # Create new camera player, add to dictionary
        cameraPlayer = CameraPlayer(dockerIp)
        cameraPlayerDictionary[dockerIp] = cameraPlayer
        
    return cameraPlayer
    
# Single View WebRtc Start
async def singleWebRtcStart(thisUUID, dockerIP, cameraName, request):
    # Pingtime holds the UUID and the current ping time (Time since last ping pong message from client, if over 5 seconds or so get rid of)
    global userUUIDAssociations
    
    # Set params from SDP Client Request to set objects
    params = ast.literal_eval((request.data).decode("UTF-8"))
    # Set offer to params parsed.
    offer = RTCSessionDescription(sdp=params.get("sdp"), type=params.get("type"))

    # Set RTCConfig Option Ice STUN Server, should be a local one incase internet is down!
    # Set ICE Server to local server, hardcoded to be NVR, change at install!
    webRtcPeer = RTCPeerConnection(configuration=RTCConfiguration(
    iceServers=[RTCIceServer(
        urls=[stunServer])]))

    # I need to call requestCameraPlayer to get a player to make readers from
    
    cameraPlayer = requestCameraPlayer(dockerIP)

    # Create tracks to tie to transceivers
    camAudioTrack = CameraPlayerTrack(cameraPlayer, 'audio', thisUUID)
    camVideoTrack = CameraPlayerTrack(cameraPlayer, 'video', thisUUID)
    
    if (camVideoTrack):
        webRtcPeer.addTransceiver(camVideoTrack, direction='sendonly')
    if (camAudioTrack):
        webRtcPeer.addTransceiver(camAudioTrack, direction='sendrecv')
    
    # We need to see if the camera supports PTZ, if it does prepare to send COORDS every second
    
    # Select all info about current cam
    myCursor.execute("Select * from localcameras where name = '{0}' ".format(cameraName))
    camtuple = myCursor.fetchall()
    camdata = camtuple[0]
    
    # Get camera model data (PTZ, Two Way Audio) from DB
    cameraModel = camdata[7]
    ptzcoords = {}
    myCursor.execute("Select hasptz, hastwa from cameradb where model = '{0}' ".format(cameraModel))
    hasEXTTuple = myCursor.fetchall()
    
    hasPTZ = hasEXTTuple[0][0]
    hasTWA = hasEXTTuple[0][1]    

    # Create Event Watcher On Data Channel To Know If Client Is Still Alive, AKA Ping - Pong
    # Also process messages from client
    @webRtcPeer.on("datachannel")
    def on_datachannel(channel):
        # Check if camera supports PTZ and/or TWA
        if (hasPTZ == True):
            ptzcoords = 'Supported' #PTZ Coords will be part of WebRTC Communication, send every 0.5 seconds.
            update_task = asyncio.create_task(updatePTZReadOut(webRtcPeer, cameraName, channel)) # Update forever until cancelled  

        if (hasTWA == True):
            if webRtcPeer.sctp.state == 'connected':
                channel.send("truetwa") # Allows Remote TWA Toggle to be clicked and processed.

        tmpCamTuple = False

        # Data channel created, on message sent from peer.
        @channel.on("message")
        async def on_message(message):
            global userUUIDAssociations
            # Won't always be connected when sending a message, try and pass here
            try:
                # Check if still connected
                if webRtcPeer.sctp.state != 'connected':
                    webRtcPeer.close()
                else:  
                    # If ping, send heartbeat pong
                    if isinstance(message, str) and message.startswith("ping"):
                        userUUIDAssociations[thisUUID][1] = time.time()
                        if webRtcPeer.sctp.state == 'connected':
                            channel.send("pong" + message[4:])
                    # If PTZ UP, send to cam.
                    elif (message.startswith("up:")):
                        msgSpeed = message.split(":")[1] 
                        sendAuthenticatedPTZContMov(cameraName, "up", msgSpeed, tmpCamTuple)
                    # If PTZ down, send to cam.
                    elif (message.startswith("down:")):
                        msgSpeed = message.split(":")[1] 
                        sendAuthenticatedPTZContMov(cameraName, "down", msgSpeed, tmpCamTuple)
                    # If PTZ left, send to cam.
                    elif message.startswith("left:"):
                        msgSpeed = message.split(":")[1] 
                        sendAuthenticatedPTZContMov(cameraName, "left", msgSpeed, tmpCamTuple)
                    # If PTZ right, send to cam.
                    elif (message.startswith("right:")):
                        msgSpeed = message.split(":")[1]
                        sendAuthenticatedPTZContMov(cameraName, "right", msgSpeed, tmpCamTuple)
                    # If PTZ positive, send to cam.
                    elif (message.startswith("positive:")):
                        msgSpeed = message.split(":")[1]
                        sendAuthenticatedPTZContMov(cameraName, "positive", msgSpeed, tmpCamTuple)
                    # If PTZ negative, send to cam.
                    elif (message.startswith("negative:")):
                        msgSpeed = message.split(":")[1]
                        sendAuthenticatedPTZContMov(cameraName, "negative", msgSpeed, tmpCamTuple)
                    # If PTZ stop, send to cam.
                    elif (message == "stop"):
                        sendAuthenticatedPTZContMov(cameraName, "stop", 0, tmpCamTuple)
                    # Client requests to do TWA, check if hasTWA and if control is requsitioned
                    elif (message == "truetwa"):         
                        if (hasTWA == True):       
                            # Get DB Details to plug in below
                            myCursor.execute("Select * from localcameras where name = '{0}' ".format(cameraName))
                            camtuple = myCursor.fetchall()
                            camdata = camtuple[0]
                            
                            # Get IP, port and slashaddress

                            cameraIP1 = camdata[2].split("//")
                            cameraIP2 = cameraIP1[1].split("/")
                            cameraIP3 = cameraIP2[0].split(":")
                                                            
                            port1 = cameraIP1[1].split(":")
                            port2 = port1[1].split("/", 1)
                            port3 = port2[0]
                            
                            slashAddress = port2[1]
                            
                            # Now stream localBuffer from WebRTC to FFMPEG and Cam
                            microphoneStreamFuture = asyncio.create_task(
                            streamBufferToRemote(camdata[3], cryptocode.decrypt(str(camdata[4]), passwordRandomKey), cameraIP3[0], int(port3), slashAddress, webRtcPeer)
                            )
                            # Add instance to uuid
                            userUUIDAssociations[thisUUID].append(microphoneStreamFuture) # Appended to 5, reserved.
                        
                    # Client requests not to do TWA.
                    elif (message == "falsetwa"):
                        if (hasTWA == True):       
                            # Send task cancel, have it SIGINT ffmpeg when occurs.
                            userUUIDAssociations[thisUUID][5].cancel()
                            await asyncio.sleep(0)
                            del userUUIDAssociations[thisUUID][5]
                        
                    # Check if cam has PTZ or TWA, then treat as toggle for requesting and giving away ticket.
                    elif (message == "requestCameraControl"):
                        if (hasPTZ == True or hasTWA == True):
                            amITheImposter = False
                            anyCamUsing = False
                            # If user wants camrea control, check userUUIDAssociations[thisUUID][3]
                            # for any cameras with this name, and if [3] is true
                            # IF I get another requestCameraControl, assume its a toggle and check if I'm true!
                            currentCam = userUUIDAssociations[thisUUID][4]
                            
                            # First check if I'M currently using the camera
                            if (userUUIDAssociations[thisUUID][3] == True):
                                # I AM USING THE CAM! User wants to relenquish control then.
                                # Send command controlbreak
                                if webRtcPeer.sctp.state == 'connected':
                                    channel.send("controlbreak")
                                # Nobodys using now
                                userUUIDAssociations[thisUUID][3] = False
                                amITheImposter = True
                            
                            if (amITheImposter == False):
                                # So we don't set our control to false then itterate on it thinking nobody had it
                                
                                for uuid in userUUIDAssociations:
                                    # print(userUUIDAssociations[uuid][4])
                                    # If the current UUID is using same cam as me, check.
                                    if userUUIDAssociations[uuid][4] == currentCam:
                                        # If they are using the camera, say so    
                                        if userUUIDAssociations[uuid][3] == True:
                                            anyCamUsing = True
                            
                                #After For loop, all uuids checked
                                # If no user is using the camera
                                if (anyCamUsing == False):
                                    # Not using, I will!
                                    if webRtcPeer.sctp.state == 'connected':
                                        channel.send("controlallow")
                                    # Set all to know I'm controlling
                                    userUUIDAssociations[thisUUID][3] = True
                                elif (anyCamUsing == True):
                                    # Is being used, control deny
                                    if webRtcPeer.sctp.state == 'connected':
                                        channel.send("controldeny")
            except:
                pass
                   
    # Wait to Set Remote Description
    await webRtcPeer.setRemoteDescription(offer)

    # Generate Answer to Give To Peer
    answer = await webRtcPeer.createAnswer()
        
    # Set Description of Peer to answer.
    await webRtcPeer.setLocalDescription(answer)

    # Set response to client from the generated objects
    final = ("{0}").format(json.dumps(
            {"sdp": (webRtcPeer.localDescription.sdp), "type": webRtcPeer.localDescription.type}
        ))
    
    # Return response to client
    return final

## MONITOR
async def monWebRtcStart(request, thisUUID, dockerIpArray, formatCamArray):
    # Access to uuidAssociations
    global userUUIDAssociations
    # Set SDP paramaters from client offer.
    params = ast.literal_eval((request.data).decode("UTF-8"))

    # Set offer object from client offer parsed
    offer = RTCSessionDescription(sdp=params.get("sdp"), type=params.get("type"))
    
    # Set peer to remote client and use the stunServer.
    webRtcPeer = RTCPeerConnection(configuration=RTCConfiguration(
    iceServers=[RTCIceServer(
        urls=[stunServer])]))
                
    # Loop and add player tracks to webRtc.
    for i, cam in enumerate(formatCamArray):

        cameraPlayer = requestCameraPlayer(dockerIpArray[i])
        camVideoTrack = CameraPlayerTrack(cameraPlayer, 'video', thisUUID)
                
        if (camVideoTrack):
            webRtcPeer.addTransceiver(camVideoTrack, direction='sendonly')
        
    # When datachannel opened, make event handler for getting a message
    @webRtcPeer.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        async def on_message(message):
            global userUUIDAssociations
            try:
                # Check if still connected
                if webRtcPeer.sctp.state != 'connected':
                    webRtcPeer.close()
                # If I get ping, go pong.
                if isinstance(message, str) and message.startswith("ping"):
                    userUUIDAssociations[thisUUID][1] = time.time()
                    if webRtcPeer.sctp.state == 'connected':
                        channel.send("pong" + message[4:])   
                elif ():
                    # print("Closing Peer!")
                    webRtcPeer.close()
            except:
                pass
                    
    # Wait to Set Remote Description
    await webRtcPeer.setRemoteDescription(offer)
    # Generate Answer to Give To Peer
    answer = await webRtcPeer.createAnswer()
    # Set Description of Peer to answer.
    await webRtcPeer.setLocalDescription(answer)
    
    # Format final response for client
    final = ("{0}").format(json.dumps(
            {"sdp": (webRtcPeer.localDescription.sdp), "type": webRtcPeer.localDescription.type}
        ))
    
    # Return response
    return final
