import socket, sys, cryptocode, hashlib, re, threading, time, websockets, subprocess, asyncio, wave, os
from pyrtp import *
from SimpleWebSocketServer import WebSocket
from io import BytesIO
from aiortc.contrib.media import MediaRelay
# File to handle functions related to two way audio,
# probe to see if camera supports it, allow for connections and start RTP blasting, all that.

def createDigestAuthString(username, password, realm, nonce, uri, method):
    # As such: Authorization: Digest username="admin", realm="Login to Amcrest",
    # nonce="8c13dafe80d4358778862c09cfef2844", uri="rtsp://10.x.x.x:554", response="2377de66c66bf2ea7699038b93f196db"
    HA1 = (hashlib.md5((username + ":" + realm + ":" + password).encode()).hexdigest())
    HA2 = (hashlib.md5((method + ":" + uri).encode()).hexdigest())
    res = (hashlib.md5((HA1 + ":" + nonce + ":" + HA2).encode()).hexdigest())

    authenticationString = ('''Authorization: Digest username="{0}", realm="{1}", nonce="{2}", uri="{3}", response="{4}"'''
    ).format(username, realm, nonce, uri, res)

    return authenticationString

def generateRTSPPacket(option, uri, userAgent, sessionNum, genAuthString=False, username='', password='', realm='', nonce='', trackID='', clientPorts={}, sessionid=''):
    # First, what option are we trying to use?
    authenticationString = ''
    if (option == "OPTIONS"):
        print("OPTIONS")
        # With sending an 'OPTIONS' request, we do the following.
        #OPTIONS rtsp://10.x.x.x:554 RTSP/1.0
        #CSeq: 1 (We assume here)
        #User-Agent: myProgram
        #Auth String (Optional)
        # We need to now generate the authenticationString, if wanted.
        if (genAuthString == True):
            authenticationString = createDigestAuthString(username, password, realm, nonce, uri, "OPTIONS")
        else:
            authenticationString = ''

        constructedPacket = ('''OPTIONS {0} RTSP/1.0\r
        CSeq: {1}\r
        User-Agent: {2}\r
        {3}\r\n\r\n''').format(uri, sessionNum, userAgent, authenticationString)

        return constructedPacket

    elif (option == "DESCRIBE"):
        print("DESCRIBE")
        # With sending an 'DESCRIBE' request, we do the following.
        # DESCRIBE rtsp://10.x.x.x:554 RTSP/1.0
        # Accept: application/sdp
        # CSeq: 3
        # User-Agent: myProgram
        # Auth String (Optional)
        if (genAuthString == True):
            authenticationString = createDigestAuthString(username, password, realm, nonce, uri, "DESCRIBE")
        else:
            authenticationString = ''

        constructedPacket = ('''DESCRIBE {0} RTSP/1.0\r
        Accept: application/sdp\r
        CSeq: {1}\r
        User-Agent: {2}\r
        {3}\r
        Require: www.onvif.org/ver20/backchannel\r\n\r\n''').format(uri, sessionNum, userAgent, authenticationString)

        return constructedPacket
    elif (option == "SETUP"):
        print("SETUP")
        # With sending an 'SETUP' request, we do the following. (We also add some extra stuff if setting up multiple tracks.)
        # SETUP rtsp://10.x.x.x:554/trackID=0 RTSP/1.0
        # Transport: RTP/AVP/UDP;unicast;client_port=14362-14363
        # x-Dynamic-Rate: 0
        # CSeq: 4
        # User-Agent: myProgram
        # Auth String (Optional)
        # OR 
        # SETUP rtsp://10.x.x.x:554/trackID=1 RTSP/1.0
        # Transport: RTP/AVP/UDP;unicast;client_port=14364-14365
        # x-Dynamic-Rate: 0
        # CSeq: 5
        # User-Agent: myProgram
        # Session: 1188118121911
        if (genAuthString == True):
            authenticationString = createDigestAuthString(username, password, realm, nonce, uri, "DESCRIBE")
        else:
            authenticationString = ''

        print(clientPorts[0], file=sys.stderr)

        constructedPacket = ('''SETUP {0}/trackID={1} RTSP/1.0\r
        Transport: RTP/AVP/UDP;unicast;client_port={2}-{3}\r
        x-Dynamic-Rate: 0\r
        CSeq: {4}\r
        User-Agent: {5}\r
        Session: {6}\r
        {7}\r
        Require: www.onvif.org/ver20/backchannel\r\n\r\n''').format(uri, trackID, clientPorts[0], clientPorts[1], sessionNum, userAgent, sessionid, authenticationString)

        return constructedPacket
        
    elif (option == "PLAY"):
        print("PLAY")
        # With sending an 'PLAY' request, we do the following.
        # PLAY rtsp://10.x.x.x:554/ RTSP/1.0
        # Range: npt=0.000-
        # CSeq: 6
        # User-Agent: myProgram
        # Session: 1188118121911
        if (genAuthString == True):
            authenticationString = createDigestAuthString(username, password, realm, nonce, uri, "DESCRIBE")
        else:
            authenticationString = ''

        constructedPacket = ('''PLAY {0} RTSP/1.0
        Range: npt=0.000-
        CSeq: {1}
        User-Agent: {2}
        Session: {3}\r
        {4}\r
        Require: www.onvif.org/ver20/backchannel\r\n\r\n''').format(uri, sessionNum, userAgent, sessionid, authenticationString)

        return constructedPacket
    elif (option == "SNAPSHOT"):
        print("SNAPSHOT")
        #Find out later
    else:
        print("Invalid Request!")
        
def createReceivingConnection(portRangeStart, portRangeEnd):
        global recvSocketStart
        global recvSocketEnd
        # print("Ports: " + str(portRangeStart) + ", " + str(portRangeEnd))
    
        recvSocketStart = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        recvSocketEnd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        server_addressStart = ('0.0.0.0', portRangeStart)
        server_addressEnd = ('0.0.0.0', portRangeEnd)
        
        recvSocketStart.bind(server_addressStart)
        recvSocketEnd.bind(server_addressEnd)
        
def determineAuthentication(firstResponse):
    authenticationType = ''
    if (firstResponse.find("401 Unauthorized") != -1):

        if (firstResponse.find("WWW-Authenticate: Digest") != -1):
            authenticationType = "Digest"
        else:
            authenticationType = "Digest"
    return authenticationType

def createConnection(ip, port):
    global rtspSocket
    rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    rtspSocket.settimeout(10)
    rtspSocket.connect((ip,port))

async def handleRTSPtoGetRTP(ip, port, address, userAgent, username, password):
    sessionPacketNum = 0; 
    payload = ''
    #First we need to contact the server and see if it uses authentication or not, and what type it uses. 
    createConnection(ip, port)
    # Generate Packet.
    sessionPacketNum = sessionPacketNum + 1;
    uri =  "rtsp://" + ip + ":" + str(port)
    payload = generateRTSPPacket("OPTIONS", userAgent=userAgent, sessionNum=sessionPacketNum, uri=uri)
    # print("Payload: " + payload)
    # Send packet and wait for response, this gives us initial session info.
    lastResponse = sendPacket(payload)
    # print("Last Response: " + lastResponse)
    # Determine authentication based on response.
    # authenticationType = determineAuthentication(lastResponse)
    authenticationType = "Digest"

    # print(("I've determined the server is using {0} authentication").format(authenticationType))

    if (authenticationType == "Digest"):
        
        tmp = re.findall(r'"([^"]*)"', lastResponse)

        realm = tmp[0]

        nonce = tmp[1]

        # A 'chunk'
        sessionPacketNum = sessionPacketNum + 1;
        payload = generateRTSPPacket("OPTIONS", userAgent=userAgent, sessionNum=sessionPacketNum, genAuthString=True, username=username, password=password, realm=realm, nonce=nonce, uri=uri)
        lastResponse = sendPacket(payload)
        # print("Payload: " + payload, file=sys.stderr)
        # print('=============================')
        # print("Response: " + lastResponse, file=sys.stderr)
        ####################################### WHAT CAN I WORK WITH?
        sessionPacketNum = sessionPacketNum + 1;
        payload = generateRTSPPacket("DESCRIBE", userAgent=userAgent, sessionNum=sessionPacketNum, genAuthString=True, username=username, password=password, realm=realm, nonce=nonce, uri=uri)
        lastResponse = sendPacket(payload)
        # print("Payload: " + payload, file=sys.stderr)
        # print('=============================')
        # print("Response: " + lastResponse, file=sys.stderr)
        ####################################### SETUP TWO WAY AUDIO ('BACKCHANNEL') (Literally just blasting RTP)
        sessionPacketNum = sessionPacketNum + 1;
        payload = generateRTSPPacket("SETUP", userAgent=userAgent, sessionNum=sessionPacketNum, genAuthString=True, username=username, password=password, realm=realm, nonce=nonce, trackID="5", clientPorts=("14368", "14369"), uri=uri)
        lastResponse = sendPacket(payload)
        # print("Payload: " + payload, file=sys.stderr)
        # print('=============================')
        # print("Response: " + lastResponse, file=sys.stderr)
        #######################################
        # Now we can setup the receiving ports for video and audio.
        # createReceivingConnection(14366, 14367)
        
        # From setup we now have the ports RTP is expected on the server, we extract those:
        remotePorts = lastResponse.split()
        remotePortsRange = remotePorts[8].split(";")
        remotePortsExtract = remotePortsRange[3].split("=")
        
        global remotePortsExtract2
        
        remotePortsExtract2 = remotePortsExtract[1].split("-")
        # print(remotePortsExtract2)
        
        # Now that sockets are setup, we can send 'play'
        sessionIdRaw = lastResponse.split()
        sessionId, timeout = sessionIdRaw[6].split(";", 1)
        sessionPacketNum = sessionPacketNum + 1;
        payload = generateRTSPPacket("PLAY", userAgent=userAgent, sessionNum=sessionPacketNum, genAuthString=True, username=username, password=password, realm=realm, nonce=nonce, sessionid=sessionId, uri="rtsp://10.x.x.x:554/trackID=5")
        lastResponse = sendPacket(payload)
        # print("Payload: " + payload, file=sys.stderr)
        # print('=============================')
        # print("Response: " + lastResponse, file=sys.stderr)
        #######################################

        #RTP Can now be received or sent based on SETUP
        
# We need to define an audio consumer class so aiortc has somewhere to put the data, thanks to phind I know how:
# https://www.phind.com/search?cache=wkoqq3lg37uvvl17xltsep86

class AudioConsumer:
    def __init__(self):
        self.audio_data = b''
        
    def write(self, data):
        print(data)
        self.audio_data += data 

# Old, redo and implement eventually.
# def streamMp3ToRTSPServerAsBackChannel(cameraIP, mp3_file):
#     command = [
#         "ffmpeg",
#         "-re",
#         "-i", mp3_file,
#         "-filter:a", """volume=-20dB""", 
#         "-vn",
#         "-acodec", "pcm_alaw",
#         "-ar", "8000",
#         "-ac", "1",
#         "-f", "rtp",
#         "rtp://{0}:{1}?localrtpport=14368&localrtcpport=14369'".format(cameraIP, remotePortsExtract2[0]),
#         "-f", "null", "-"
#     ]
    
#     # print(command)
    
#     process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
#      # Wait for the command to finish
#     stdout, stderr = process.communicate()

#     # Print any output from FFmpeg
#     if stdout:
#         print(stdout.decode())
#     if stderr:
#         print(stderr.decode())
        
def sendPacket(payload):
    rtspSocket.send(payload.encode())
    return rtspSocket.recv(4096).decode("UTF-8")

async def streamBufferToRemote(username, password, cameraIP, port, slashAddress, webrtcpeer):
    # print("STREAM BUFFER TO REMOTE")
    await handleRTSPtoGetRTP(cameraIP, port, slashAddress, "zemond/1.0", username, password)
    
    localBuffer = BytesIO()
    frontBuffer = BytesIO()
    
    receiver = webrtcpeer.getReceivers()[1]
    
    relay = MediaRelay()
    audioTrack = receiver.track
    proxy_track = relay.subscribe(audioTrack)
    
    # THIS FINALLY WORKS! However it takes about 5 seconds for the audio to connect, can be fixed in future!
    
    
    command = " ".join([
        "ffmpeg",
        "-re",
        "-itsoffset", "-00:00:8", 
        "-c:a", "pcm_s16le",
        "-i", "pipe:0",
        "-v", "trace", 
        "-vn",
        "-acodec", "pcm_alaw",
        "-filter:a", """volume=-10dB""", 
        "-ar", "8000",
        "-ac", "1",
        "-f", "rtp",
        "rtp://{0}:{1}?localrtpport=14368&localrtcpport=14369'".format(cameraIP, remotePortsExtract2[0])
    ])
    
    process = await asyncio.create_subprocess_exec(*command.split(), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    
    async def updateAudioBufferLoop():
        doOnce = False;
        while True:
            try:
                # print("AWAIT AUDIO DATA")
                audioFrame = await audioTrack.recv()
                if audioFrame is None:
                    print("NO AUDIO")
                    break
                
                # print(audioFrame.format)
                # print(audioFrame)
                localBuffer.seek(0)  
                localBuffer.write(audioFrame.to_ndarray().tobytes())
                localBuffer.seek(0)
                frontBuffer = localBuffer.read()
                process.stdin.write(frontBuffer)
                # print("Start Drain")
                # await process.stdin.drain()
                # print("Latest packet checksum: " + str(hashlib.md5(frontBuffer).hexdigest()))

            except Exception as e:
                print("Error In Retrieving WebRTC Incoming Audio Data, exception follows: " + str(e))
                process.stdin.close()
                await process.wait()
            
    
    # KNOWN FACT: NO FFMPEG OUTPUT UNLESS IT'S FINISHED,
    # Theory: FFMPEG is not quiting early anymore because or -re, but still will not accept the buffer pipe:0 in, I think...
    # It dosen't seem to crash when I just do frontBuffer, not .getValue, so I want to quit it early to see it's statistics.
    
    update_task = asyncio.create_task(updateAudioBufferLoop())
    stdout, stderr = await process.communicate()

    # # # Print any output from FFmpeg
    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())
        
        
def describePROBE(username, password, ip, port, slashAddress, userAgent):
    # print("Probing for TWO WAY AUDIO RTSP sendonly")
    
    hasTWA = False
    
    sessionPacketNum = 0; 
    payload = ''
    #First we need to contact the server and see if it uses authentication or not, and what type it uses. 
    createConnection(ip, port)
    # Generate Packet.
    sessionPacketNum = sessionPacketNum + 1;
    uri =  "rtsp://" + ip + ":" + str(port)
    payload = generateRTSPPacket("OPTIONS", userAgent=userAgent, sessionNum=sessionPacketNum, uri=uri)
    # print("Payload: " + payload)
    # Send packet and wait for response, this gives us initial session info.
    lastResponse = sendPacket(payload)
    # print("Last Response: " + lastResponse)
    # Almost always DIGEST, will implement basic when I see a camera that does it.
    # authenticationType = determineAuthentication(lastResponse)
    authenticationType = "Digest"

    # print(("Determined the server is using {0} authentication").format(authenticationType))
    
    tmp = re.findall(r'"([^"]*)"', lastResponse)

    realm = tmp[0]

    nonce = tmp[1]
    
    sessionPacketNum = sessionPacketNum + 1;
    payload = generateRTSPPacket("OPTIONS", userAgent=userAgent, sessionNum=sessionPacketNum, genAuthString=True, username=username, password=password, realm=realm, nonce=nonce, uri=uri)
    lastResponse = sendPacket(payload)
    # print("Payload: " + payload, file=sys.stderr)
    # print('=============================')
    # print("Response: " + lastResponse, file=sys.stderr)
    ####################################### WHAT CAN I WORK WITH?
    sessionPacketNum = sessionPacketNum + 1;
    payload = generateRTSPPacket("DESCRIBE", userAgent=userAgent, sessionNum=sessionPacketNum, genAuthString=True, username=username, password=password, realm=realm, nonce=nonce, uri=uri)
    lastResponse = sendPacket(payload)
    # print("Payload: " + payload, file=sys.stderr)
    # print('=============================')
    # print("Response: " + lastResponse, file=sys.stderr)
    
    
    # Now we have SDP, see if 'a=sendonly' is present, if it is we have two way audio!
    
    if 'a=sendonly' in lastResponse:
        hasTWA = True
        
    return hasTWA