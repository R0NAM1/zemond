from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory
from flask_sock import Sock 
from functools import wraps
from bs4 import BeautifulSoup
from io import BytesIO
from threading import Thread, active_count
from waitress import serve # Production server
import cryptocode, av, websockets, time, ast, logging, cv2, sys, os, psycopg2, argparse, asyncio, json, logging, ssl, uuid, base64

# WebRTC
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer, MediaRelay
from aiortc.rtcrtpsender import RTCRtpSender

#import Zemond Specific Parts
from onvifRequests import *
from onvifAutoConfig import onvifAutoconfigure
from globalFunctions import passwordRandomKey, myCursor, myDatabase, sendONVIFRequest
from dockerComposer import addRunningContainer

app = Flask(__name__)

app.secret_key = 'IShouldBeUnique!' # Change this, as it's just good practive, generate some random hash string.

global snapshotCache;

pingTime = {}

# ONVIF URL STANDARD: http(s)://ip.address/onvif/device_serivce 

# login required decorator
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap

# By default, route to the dashboard.
@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

# Route for handling the login page logic
# No user logic yet, only admin. Future options will be:
# Built in, LDAP, AD by group linking. 
@app.route('/login/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'admin':
            error = 'Invalid Credentials. Please try again.'
        else:
            session['logged_in'] = True
            flash('Your logged in!')
            return redirect(url_for('index'))
    return render_template('login.html', error=error)

@app.route('/logout/')
@login_required
def logout():
    session.pop('logged_in', None) # Pop goes the user session!
    flash('You were logged out.')
    return redirect(url_for('index'))

@app.route('/dashboard/')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/cameralist/')
@login_required
def cameraList():

    global snapshotCache

    # Unlike lastime to build the table this time we need to assemble the final tuple here in script
    myCursor.execute("Select * from localcameras ORDER BY name ASC")
    localcameras = myCursor.fetchall()
    myCursor.execute("Select * from cameradb")
    cameradb = myCursor.fetchall()

    # Data structure to send: Snapshot, Camera Name, Model & Serial, Camera Image

    # To process: Get All From Local Cameras, associate with model number, using that 'add' data to the tuple
    dataToSend = None;


    for row in localcameras:
        # Get Current Name
        currentiname = row[0]
        # First Generate Snapshot,
         # Get Name's RTSP URI with username and password
        currentiurlString = row[2]

        # Create httpurl
        #http://ip.address/onvif/device_service
        httpurl = row[1]
        httpurl = httpurl.replace("/onvif/device_service", "")
        
        # Parse Snapshot Cache and get correct image in Iteration

        iterativeSnapshot = snapshotCache.get(currentiname)


       
        # Get Name's Model Number
        myCursor.execute("Select model from localcameras where name='{0}'".format(currentiname))
        currentimodel = myCursor.fetchone()
        currentimodelString = ''.join(currentimodel)
        # Get Image From Model Number
        myCursor.execute("Select image from cameradb where model='{0}'".format(currentimodelString))
        imageToLoad = myCursor.fetchone()
        imageToLoadString = ''.join(imageToLoad)

        # Create Info String For ManMod

         # Get Name's Manufacturer
        myCursor.execute("Select manufacturer from cameradb where model='{0}'".format(currentimodelString))
        currentimanufacturer = myCursor.fetchone()
        currentimanufacturerString = ''.join(currentimanufacturer)

        manmod = currentimanufacturerString + " " + currentimodelString

        # Can't Have Spaces In A URL, So Quickly Parse That.
        parsedName = str(row[0]).replace(" ","%20") 

        # If data is empty add data, if not then append.
        if dataToSend == None:
            dataToSend = ((iterativeSnapshot, row[0], manmod, imageToLoadString, httpurl, parsedName), )
        else:
            rawData = ((iterativeSnapshot, row[0], manmod, imageToLoadString, httpurl, parsedName), )
            dataToSend = (dataToSend) + (rawData)

            


    # dataToSend = (("Snapshot", "Name", "Model + Serial", "Camera Image", "httpurl"), ("Snapshot", "Name", "Model + Serial", "Camera Image", "httpurl"))

    return render_template('cameralist.html', data=dataToSend)

@app.route('/settings/')
@login_required
def settings():
    return render_template('settings.html')

# This one is automatic
@app.route('/settings/add_camera/', methods=['GET', 'POST'])
@login_required
def addCamera():
    if request.method == 'POST':
        cameraname = request.form['cameraname']
        onvifURL = request.form['onvifURL']
        username = request.form['username']
        password = request.form['password']
        if not onvifURL:
            session.pop('_flashes', None)
            flash('ONVIF URL is required!')
        elif not username:
            session.pop('_flashes', None)
            flash('Username is required!')
        elif not password:
            session.pop('_flashes', None)
            flash('Password is required!')
        else:
            # Quick check to see if camera already exists in DB
            doesCameraNameExist = myCursor.execute("Select Name from localcameras Where name = '{0}'".format(cameraname))
            fetchabove = myCursor.fetchall()
            if  (myCursor.rowcount != 0):
                session.pop('_flashes', None)
                flash('Camera With Same Name Exists!')
            else:
                # Before storing all this, we need to verify a few things:
                # Credentials must be correct and ONVIF must be supported.
                # Server will give a 401 Unauth if Credentials are wrong
                # A Un-Parseable resoinse if ONVIF is not supported, 200 If it is with what's expected from GetDeviceInfomation

                # Send GetDeviceInfomation and determine action.

                try:
                    response = sendONVIFRequest(GetDeviceInformation, onvifURL, username, password)
                except Exception as e:
                        # Camera does not support onvif!
                        session.pop('_flashes', None)
                        flash('Camera does not seem to support Onvif, the following exception was raised: ' + str(e))
                else:

                    parsedResponseXML = BeautifulSoup(response.text, 'xml')

                    print(response.text)

                    if (response.text.find("NotAuthorized") != -1):
                        session.pop('_flashes', None)
                        flash('Credentials Are Incorrect!')
                    else:
                        try:
                            cameraManufacturer = parsedResponseXML.find_all('tds:Manufacturer')[0].text
                        except:
                            # Camera does not support onvif!
                            session.pop('_flashes', None)
                            flash('Camera does not seem to support Onvif, it gave the following response:' + response.text)
                        else:
                            # Now add credentials to DB, make sure to encrypt the password for storage!
                            passwordEncrypted = cryptocode.encrypt(password, passwordRandomKey)
                            try:
                                myCursor.execute("INSERT INTO localcameras (name, onvifURL, username, password) VALUES(%s, %s, %s, %s)", (cameraname, onvifURL, username, passwordEncrypted))
                            except Exception as e:
                                session.pop('_flashes', None)
                                flash('Database couldnt be written to, the following exception was raised: ' + str(e))
                            else:
                                myDatabase.commit()
                                # Now we can get info and do all info scraping using ONVIF
                                onvifAutoconfigure(cameraname)

                                # After ONVIF autoconfigure is complete, create recording Docker Container.
                                
                                #Create RTSP Cred String:
                                    # Get RTSP URL
                                # Get Name's RTSP URI with username and password
                                myCursor.execute("Select rtspurl from localcameras where name='{0}'".format(cameraname))
                                currentiurl = myCursor.fetchone()
                                currentiurlString = ''.join(currentiurl)
                                # Get Current Camera's Username
                                myCursor.execute("Select username from localcameras where name='{0}'".format(cameraname))
                                currentiusername = myCursor.fetchone()
                                currentiusernameString = ''.join(currentiusername)
                                # Get Current Camera's Password
                                myCursor.execute("Select password from localcameras where name='{0}'".format(cameraname))
                                currentipassword = myCursor.fetchone()
                                currentipasswordString = ''.join(currentipassword)

                                myCursor.execute("Select rtspurl from localcameras where name='{0}'".format(cameraname))
                                rtspurl =  myCursor.fetchone()
                                rtspurl =  ''.join(rtspurl)
                                rtspurl2 = rtspurl.replace("rtsp://", "")
                                ip, port = rtspurl2.split(":", 1)
                                port = port.split("/", 1)[0]
                                address, params = rtspurl.split("/cam", 1)
                                rtspCredString = currentiurlString[:7] + currentiusernameString + ":" + cryptocode.decrypt(str(currentipasswordString), passwordRandomKey) + "@" + currentiurlString[7:]
                               
                                addRunningContainer(cameraname, rtspCredString, "268435456", "48")
                                return redirect(url_for('dashboard'))

    return render_template('add_camera.html')

# Manual, if having to use non-ONVIF RTSP video sources
@app.route('/settings/add_camera_manual/', methods=['GET', 'POST'])
@login_required
def addCameraManual():
    if request.method == 'POST':
        cameraname = request.form['cameraname']
        onvifURL = request.form['onvifURL']
        username = request.form['username']
        password = request.form['password']
        rtspurl = request.form['rtspurl']
        manufacturer = request.form['manufacturer']
        model = request.form['model']
        serialnumber = request.form['serialnumber']
        firmwareversion = request.form['firmwareversion']
        
        # Quick check to see if camera already exists in DB.
        doesCameraNameExist = myCursor.execute("Select Name from localcameras Where name = '{0}'".format(cameraname))
        fetchabove = myCursor.fetchall()
        if  (myCursor.rowcount != 0):
            session.pop('_flashes', None)
            flash('Camera With Same Name Exists!')
        else:
            # Now add credentials to DB, make sure to encrypt the password for storage!
            passwordEncrypted = cryptocode.encrypt(password, passwordRandomKey)
            myCursor.execute("INSERT INTO localcameras (name, onvifURL, username, password, rtspurl, manufacturer, model, serialnumber, firmwareversion) VALUES(%s, %s, %s, %s,%s, %s, %s, %s, %s)", (cameraname, onvifURL, username, passwordEncrypted, rtspurl, manufacturer, model, serialnumber, firmwareversion))
            myCursor.execute("INSERT INTO cameradb (model, manufacturer, hasptz, hastwa) VALUES(%s, %s, %s, %s)", (model, manufacturer, False, False))
            myDatabase.commit()

            return redirect(url_for('dashboard'))
    return render_template('add_camera_manual.html')

# List all camera models gathered over time
@app.route('/settings/camera_models/', methods=['GET', 'POST'])
@login_required
def cameraModels():
    if request.method == 'POST':
        if 'cameraimage' not in request.files:
            return 'cameraimage not in form!'
        selectedModel = request.form['submit_button']
        imageFile = request.files['cameraimage'].read()
        imageb64 = str(base64.b64encode(imageFile).decode("utf-8"))
        # Should be data:image/png;base64,iVBORw0KGgo
        myCursor.execute("UPDATE cameradb SET image=(%s) WHERE model = '{0}'".format(selectedModel), (imageb64, ))
        myDatabase.commit()

    myCursor.execute("Select * from cameradb")
    cameradb = myCursor.fetchall()
    allCameraModels = ''.join(str(cameradb))
    return render_template('camera_models.html', data=cameradb)


# Return Favicon
@app.route('/favicon.ico')
def returnIcon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'pictures/logo.png',mimetype='image/vnd.microsoft.icon')

# View a camera, using WebRTC, and ONVIF Event Logs, with Recording Information and quick view, plus a link to the camera.
@app.route('/view_camera/<cam>', methods=['GET', 'POST'])
@login_required
def viewCamera(cam):
    global player

    # To view the camera, we need to custom make the data we are going to pass over, like in the Camera List. Formatted as follows:
    # Name, Manufacturer, Model Number, Serial, Firmware, CameraImage, IP. 
    
    # Generate Static Data
    myCursor.execute("Select * from localcameras where name = '{0}' ".format(cam))
    camtuple = myCursor.fetchall()
    camdata = camtuple[0]
    # Currently passing through the raw DB query.

   

    # Below is WEBRTC Code, it is partially complex, but not really.
    # Both the client and server implement 'RTCRemotePeer' and can exchange SDP with HTTP POST. Use that SDP with the Peer and you
    # Have a remote WebRTC Peer you can send video to! All processing and reconstruction is done on the client side.

    # First we need to generate the raw datastream from the RTSP URL, we'll call another thread to do this, as it's temporary.
    # This writes a frame to the POST url buffer and consistantly updates it, 



    # Used to use RTSPCredString to connect to camera directly, now connecting to local RTSP proxy.



    return render_template('view_camera.html', data=camdata)  









# WEBRTC ===================================
# This is what runs forever, while the client is connected,
# MASSIVELY SCREWEY DUE TO ME NOT KNOWING HOW TO THREAD PROPERLY.

def webRtcWatchdog(uuid, rtcloop):
    global pingTime
    global watchdog
    time.sleep(5) # Wait at least 5 seconds for client to connect.
    while True:
        time.sleep(1)
        # If timer exceeds value, then run thread.stop;

        # print("Current UUID for session is: " + str(uuid))

        # print(pingTime[uuid])

        diffTime = float(time.time()) - float(pingTime[uuid]) # Need to add a UUID along WITH pingtime so sessions don't intermix.

        # print("Diff Time: " + str(diffTime))

        if (diffTime > 5.0):
            print("Running Threads Before: " + str(active_count()))
            rtcloop.stop() # This tells the Event Loop to stop executing code, but it does not CLOSE the loop! (Which leaves 1 cascading thread!)
            time.sleep(3) # Wait three seconds for code to stop executing...
            rtcloop.close() #  Close event loop, which reduces thread count back to what it was originally. <---- THIS WAS A BIG FIX
            print("Running Threads After: " + str(active_count()))
            break
    print("Broken Watchdog, thread should be terminating now!")

async def webRtcStart(uuid, dockerIP):


    global pingTime

    thisUUID = uuid

    # pingTime = {thisUUID: ""}

    pingTime[thisUUID] = ""
    
    # Get current loop
    loop = asyncio.get_event_loop()
        
    # Set Media Source and decode offered data
    player = MediaPlayer("rtsp://" + dockerIP + ":8554/cam1") # In the future the media source will be the local relay docker container that has the camera in question, instead of from the camera itself.
    params = ast.literal_eval((request.data).decode("UTF-8"))

    # Set ICE Server to local server CURRENTLY STATIC
    offer = RTCSessionDescription(sdp=params.get("sdp"), type=params.get("type"))
    webRtcPeer = RTCPeerConnection(configuration=RTCConfiguration(
    iceServers=[RTCIceServer(
        urls=['stun:nvr.internal.my.domain'])]))

    

    # Create Event Watcher On Data Channel To Know If Client Is Still Alive, AKA Ping - Pong

    @webRtcPeer.on("datachannel")
    def on_datachannel(channel):
        @channel.on("message")
        def on_message(message):
            global pingTime
            if isinstance(message, str) and message.startswith("ping"):
                pingTime[thisUUID] = time.time()
                channel.send("pong" + message[4:])
            elif ():
                print("Closing Peer!")
                webRtcPeer.close()

    if (player.video):
        webRtcPeer.addTrack(player.video)
    if (player.audio):
        webRtcPeer.addTrack(player.audio)

    # Wait to Set Remote Description
    await webRtcPeer.setRemoteDescription(offer)

    # Generate Answer to Give To Peer
    answer = await webRtcPeer.createAnswer()

    # Set Description of Peer to answer.
    await webRtcPeer.setLocalDescription(answer)

    final = ("{0}").format(json.dumps(
            {"sdp": (webRtcPeer.localDescription.sdp), "type": webRtcPeer.localDescription.type}
        ))

    # Retirn response
    return final

# When we grab a WebRTC offer
@app.route('/rtcoffer/<cam>', methods=['GET', 'POST'])
@login_required
def webRTCOFFER(cam):

    global webRTCThread
    global watchdog

    # Get Docker IP
    # Get Name's Docker IP with username and password
    myCursor.execute("Select dockerIP from localcameras where name='{0}'".format(cam))
    dockerIP = myCursor.fetchone()
    dockerIPString = ''.join(dockerIP)

    # When running to return a variable, we need to set a server side UUID so sessions don't get muxxed together.

    thisUUID = str(uuid.uuid4()) # Generate a UUID for this session.

    # Always create a new event loop for this session.
    rtcloop = asyncio.new_event_loop()
    asyncio.set_event_loop(rtcloop)
        
    # Run an event into that loop until it's complete and returns a value
    t = rtcloop.run_until_complete(webRtcStart(thisUUID, dockerIPString))
    

    # Now create a timer that is reset by Ping-Pong.

    # Continue running that loop forever to keep AioRTC Objects In Memory Executing, while shifting it to
    # Another thread so we don't block the code.
    webRTCThread = Thread(target=rtcloop.run_forever)
    webRTCThread.start()
    watchdog = Thread(target=webRtcWatchdog, args=(thisUUID, rtcloop, )) # Create a watchdog that takes the UUID and Event Loop
    watchdog.start()

    # print("Current Number Of Running Threads: " + str(active_count()))
    
    # Return Our Parsed SDP
    return t.encode()


# WEBRTC END ===================================

def updateSnapshots():

    while True:
        # This runs infinitly in another thread at program start,
        # this gets a list of all the cameras, creates a string for each of them, (Perhaps one array, or tuple), then gets
        # a snapshot of it, and stores it. They can be called anytime.

        myCursor.execute("Select * from localcameras")
        localcameras = myCursor.fetchall()

        global snapshotCache

        # Reset Temp Cache

        tempCacne = {}

        for row in localcameras:
            # Get Current Name
            currentiname = row[0]
            # First Generate Snapshot,
            # Get Name's RTSP URI with username and password
            currentiurlString = row[2]
            currentiusernameString = row[3]
            # Get Current Camera's Password
            currentipasswordString = row[4]

            # Assemble Credential Based RTSP URL
            rtspCredString = 'rtsp://' + row[10] + ':8554/cam1'

            os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
            cap = cv2.VideoCapture(rtspCredString)
            

            if not cap.isOpened():
                print('Cannot open RTSP stream')
            else:
                readquestion, frame = cap.read()
                # print("Got Snapshot for " + currentiname)
                cap.release()

            _, im_arr = cv2.imencode('.jpg', frame)  # im_arr: image in Numpy one-dim array format.
            im_bytes = im_arr.tobytes()
            im_b64 = base64.b64encode(im_bytes).decode("utf-8") # Base 64 Snapshot

            # Add data to dictionary as Name : IMG
            tempCacne[currentiname]=im_b64

        snapshotCache = tempCacne; # When temp Cache is finished filling, finalize it.
        print("Running Threads: " + str(active_count())) # We currently don't ever stop the started threads as
        time.sleep(15) # Time to wait between gathering snapshots

if __name__ == '__main__':
    # Start Snapshot Thread.
    snapshotThread = Thread(target=updateSnapshots)
    snapshotThread.start()
    # Testing Web Server
    # app.run(host='0.0.0.0')

    # Production web server
    serve(app, host='0.0.0.0', port=5000)