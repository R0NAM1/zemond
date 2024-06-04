import cryptocode, av, websockets, time, ast, logging, cv2, sys, os, psycopg2, argparse, asyncio, json, logging, ssl, uuid, base64, queue, signal, threading, dockerComposer # Have to import for just firstRun because of global weirdness
import tracemalloc, logging, m3u8, globalFunctions, psutil
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory, Markup, make_response, jsonify, send_file, Response
from flask_sock import Sock
from flask_login import LoginManager, UserMixin, login_user, current_user
from functools import wraps
from bs4 import BeautifulSoup
from io import BytesIO
from threading import Thread, active_count
from git import Repo
from waitress import serve # Production server
from sqlescapy import sqlescape

# COMMENT TO SEE FFMPEG OUTPUT, OR ADD TRACE
os.environ['AV_LOG_LEVEL'] = 'quiet'
# WebRTC
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCDataChannel
from aiortc.contrib.media import MediaPlayer, MediaRelay, MediaBlackhole
from aiortc.rtcrtpsender import RTCRtpSender

#import Zemond Specific Parts
from onvifRequests import *
from onvifAutoConfig import onvifAutoconfigure
from globalFunctions import passwordRandomKey, myCursor, myDatabase, sendONVIFRequest, userUUIDAssociations, sigint
from dockerComposer import addRunningContainer, dockerWatcher, removeContainerCompletely, firstRunDockerCheck
from ptzHandler import readPTZCoords, sendContMovCommand, sendAuthenticatedPTZContMov, updatePTZReadOut
from twoWayAudio import streamBufferToRemote
from userManagement import createUser, verifyDbUser, resetUserPass, verifyUserPassword, auditUser, cameraPermission, sendAuditLog
from permissionTree import permissionTreeObject
from webRtc import singleWebRtcStart, monWebRtcStart, stunServer, rtcWatchdog

app = Flask(__name__)
login_manager = LoginManager(app)
login_manager.init_app(app)

app.secret_key = 'IShouldBeUnique!' # Change this, as it's just good practice, generate some random hash string.

# app.config.update(
#     SESSION_COOKIE_SECURE=True,
#     SESSION_COOKIE_SAMESITE='None',
# )

# Customer User object that Flask_login requires, just takes a string and returns it as self.username (User(username))
# Also returns other flaskio funnies, is_active True, is_anon False, I handle all that logic.
class User(UserMixin):
    def __init__(self, username):
        self.username = username
    # All users can login
    def is_active(self):
        return True
    def is_anonymous(self):
        return False
    # Return username as ID
    def get_id(self):
        return self.username

global snapshotCache, userUUIDAssociations, sigint;


release_id = 'Alpha 0.9.0'

commit_id = ''

# ONVIF URL STANDARD: http(s)://ip.address/onvif/device_serivce 

def sigint_handler(signum ,frame):
    print("SIGINT Received, exiting...")
    # Kill all UUID webrtc live events
    
    global sigint;
    sigint = True
    
    # for uuid in userUUIDAssociations:
    #     iLoop = userUUIDAssociations[uuid][2]
    #     iLoop.stop() # This tells the Event Loop to stop executing code, but it does not CLOSE the loop! (Which leaves 1 cascading thread!)
    #     time.sleep(1) # Wait one seconds for code to stop executing...
    #     iLoop.close() #  Close event loop, which reduces thread count back to what it was originally. <---- THIS WAS A BIG FIX
    #     del userUUIDAssociations[uuid]
    
    # Cancel All Tasks
    # tasks = asyncio.all_tasks()
    # for task in tasks:
    #     task.cancel()
    
    sys.exit(0)

def setCommitID():
    global commit_id
    repo = Repo("./")
    commit_id = repo.head.commit.hexsha
    commit_id = commit_id[:10] + "..."

# If not logged_in, make em!
# If there is no request.url, redirect to dashboard
# Else, redirect to request.url
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
            session['wants_url'] = request.url
            return redirect(url_for('login'))
    return wrap

# Required Flaskio Decorator, calls my required User object that Flaskio likes
@login_manager.user_loader
def load_user(username):
    return User(username)

# Redirect to the dashboard if at root index
@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

# Route for handling the login page logic
@app.route('/login/', methods=['GET', 'POST'])
def login():
    session.pop('_flashes', None)
    error = None
    # POST REQUEST
    if request.method == 'POST':
        # Get inputted username and password, sanitize
        inputtedUsername = request.form['username']
        inputtedPassword = request.form['password']
        
        # Sanitize inputs with sqlescapy sqlescape object
        santizedUsername = sqlescape(inputtedUsername)
        santizedPassword = sqlescape(inputtedPassword)
        
        # Check if user actually exists in database
        if (auditUser(santizedUsername, "permissionRoot.userSettings.accountActive")):
            # DO HERE incase somebody is bruteforcing logins with different names, real or not.
            if verifyUserPassword(santizedUsername, santizedPassword):
                # Verified password, permit login (Eventually integrate 2FA with FIDO or U2F)
                # Set user object for flask to santizedUsername
                # Register user with flask session by passing in username as string, and it makes it a user object same character set as string
                # "user" --> user (as instance of User())
                localUserObject = User(santizedUsername)
                # Login user to flask with flaskUser object
                login_user(localUserObject)
                # Set client session cookie logged_in to true so can access any page
                session['logged_in'] = True
                session.pop('_flashes', None)
                # Debug for finding issues with cookies
                # print(session)
                # Log in code should be finished
                flash('Your logged in!')
                # Redirect to dashboard when finished if requestedUrl is None, else redirect to requestedUrl
                if session['wants_url'] is None:
                    return redirect(url_for('dashboard'))
                else:
                    return redirect(session['wants_url'])
            else:
                # Could not verify password, give generic message
                session.pop('_flashes', None)
                flash('Username or Password is incorrect!')
        else:
            # If we could not find account, give generic message
            session.pop('_flashes', None)
            flash('Username or Password is incorrect!')
        ## END POST

    # GET REQUEST
    return render_template('login.html', error=error, commit_id=commit_id, release_id=release_id)

@app.route('/logout/')
@login_required
def logout():
    session.pop('logged_in', None) # Pop goes the user session!
    flash('You were logged out for the following reason:')
    return redirect(url_for('index'))

@app.route('/dashboard/')
@login_required
def dashboard():
    session.pop('_flashes', None)
    # Permission Check Dashboard
    if (auditUser(current_user.username, "permissionRoot.dashboard")):
        # Return general stats, num cameras online, offline, usersloggedin,
        # Grab total number of cameras from database
        myCursor.execute("Select name from localcameras;")
        localcameras = myCursor.fetchall()
        totalCamNum = len(localcameras)
        offlineCamNum = (totalCamNum - onlineCameraCache)
        # print(str(login_manager._login_disabled))
        return render_template('dashboard.html', userArray=globalFunctions.sessionsArray, systemCpu=globalFunctions.systemCpu, systemMem=globalFunctions.systemMem, threadsArray=globalFunctions.threadsArray, threadsActive=globalFunctions.threadsRunning, camerasonline=onlineCameraCache, offlineCamNum=offlineCamNum, commit_id=commit_id, release_id=release_id) #onlineCameraCache current amount of cameras
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.dashboard", commit_id=commit_id, release_id=release_id)

@app.route('/monitors/', methods=['GET', 'POST'])
@login_required
def monitors():
    session.pop('_flashes', None)
    # For XBX, camarray is just cameras, slideshow is either a camera, or monitor. For map, is just list of cameras
    
    if (auditUser(current_user.username, "permissionRoot.monitors")):
        if request.method == 'POST':
        # Only post we should be getting is request to delete monitor
            # Want to delete monitor
            if 'deleteMonitor' in str(request.data.decode()):
                monToDelete = (str(request.data.decode()).split(':'))[1]
                
                # Try to run DB delete query, if it fails continue
                try:
                    myCursor.execute("DELETE FROM configuredMonitors where monitorName='{0}'".format(monToDelete))
                    myDatabase.commit()
                    
                    # Respond TRUE to reload monitor page
                    return make_response('TRUE', 200)
                except:
                    pass
            # Want to upload new map
            elif 'uploadMap' in str(request.data.decode()):
                # Upload data to db, then send TRUE
                # Split data
                splitData = (str(request.data.decode())).split(':')
                # 0 is command, 1 is new name, 2 is image data
                newName = splitData[1]
                image = splitData[2].replace('image/png;base64,', '')
                
                try:
                    myCursor.execute("INSERT INTO mapData (mapName, image) VALUES (%s, %s);", (newName, image))
                    myDatabase.commit()
                    return make_response('TRUE', 200)
                except Exception as e:
                    print("Exception, " + str(e))
                    return make_response('FALSE', 200)
                    pass
            # Update existing map
            elif 'updateMap' in str(request.data.decode()):
                # Upload data to db, then send TRUE
                # Split data
                splitData = (str(request.data.decode())).split(':')
                # 0 is command, 1 is new name, 2 is image data
                newName = splitData[1]
                image = splitData[2].replace('image/png;base64,', '')
                
                try:
                    myCursor.execute("UPDATE mapData SET image = %s WHERE mapName = %s;", (image, newName));
                    myDatabase.commit()
                    return make_response('TRUE', 200)
                except Exception as e:
                    print("Exception, " + str(e))
                    return make_response('FALSE', 200)
                    pass  
            # Delete a map
            elif 'deleteMap' in str(request.data.decode()):
                # Split data
                splitData = (str(request.data.decode())).split(':')
                # 0 is command, 1 is new name, 2 is image data
                mapName = splitData[1]
                
                try:
                    # Try to delete
                    myCursor.execute("DELETE FROM mapData where mapName='{0}'".format(mapName))
                    myDatabase.commit()
                    return make_response('TRUE', 200)
                except Exception as e:
                    print("Exception, " + str(e))
                    return make_response('FALSE', 200)
                    pass
            # END POST
        # GET REQUEST
        
        # Two tabs, added monitors, add monitor, left would show all configured monitors in the db, while right would show templates
        # cameras and maps would be plugged into.
        
        # Proposed templates:
        # - X by X camera array, can scale, can be timed to roll to each.
        # - Single Camera Mode, with map at bottom right
        # - More later...
        # 'Templates' are just editors. Click on add new and brings up the specific new editor.
        
        # Grab Monitor lists, types.
        myCursor.execute("Select monitorName, monitortemplate from configuredMonitors WHERE monitortemplate = 'xbx' ORDER BY monitorName ASC;")
        gridMon = myCursor.fetchall()
        
        myCursor.execute("Select monitorName, monitortemplate from configuredMonitors WHERE monitortemplate = 'slideshow' ORDER BY monitorName ASC;")
        slideMon = myCursor.fetchall()
        
        myCursor.execute("Select monitorName, monitortemplate from configuredMonitors WHERE monitortemplate = 'map' ORDER BY monitorName ASC;")
        mapMon = myCursor.fetchall()
        
        # Grab maps
        myCursor.execute("Select mapname, image from mapData ORDER BY mapname ASC;")
        mapList = myCursor.fetchall()
        
        return render_template('monitors.html', gridMon=gridMon, slideMon=slideMon, mapMon=mapMon, mapList=mapList, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.monitors", commit_id=commit_id, release_id=release_id)
# Will Allow FNAF Mode, single monitor mode, multi-monitor mode, premade views, true power!

@app.route('/monitors/view/<monitor>')
@login_required
def view_monitor(monitor):
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.monitors.view")):
        # Check type of monitor, serve specific JS file for different type
        # xbxview.js, fnafmode.js
        monitorjsfile = "non"
        # Set default delta incase of errors
        delta = 5
        
        # Get monitor name and template, verifies it exists.
        myCursor.execute("Select monitorName, monitortemplate from configuredMonitors WHERE monitorName='{0}';".format(monitor))
        monList = myCursor.fetchall()[0]
        
        # Use logic for Grid                
        if monList[1] == "xbx":
            # If loading just a grid montitor, get it's dbinfo and then the array of camreas to stream
            # Load XBXVIEW js file
            monitorjsfile = "xbxview"
            # Info about single monitor
            myCursor.execute("Select lengthbywidthnum, timeinfo from configuredMonitors WHERE monitorName = '{0}';".format(monitor))
            dbinfo = myCursor.fetchone()
            # All cameras to display
            myCursor.execute("Select camarray from configuredMonitors WHERE monitorName = '{0}';".format(monitor))
            # Set final CAMARRAY
            camarray = str(myCursor.fetchone())
            
        # Use logic for slideshow
        elif monList[1] == "slideshow":
            # Need to load camarray, and then all XBX info!
            monitorjsfile = "slideshowview"
            # Init empty objects
            dbinfo = []
            camArrayTemp = []
            # Get array of cams
            myCursor.execute("Select camarray from configuredMonitors WHERE monitorName = '{0}';".format(monitor))
            # Process array for HTTP sending
            array = (str(myCursor.fetchone()[0]))
            array = array.replace("'", '"')
            # Set final CAMARRAY
            camarray = json.loads(array)
            
            # Loop through each camarray item and clean up
            for key, value in camarray.items():
                # VALUE is type:name     
                for key, no in value.items():
                    # no is just {}, empty, ignore.
                    # KEY is type:name, determine type, 
                    key = key.split(':')
                    
                    # If CAM, just add dockerIp,
                    # IF MON, get all docker ips and add to dbinfo
                    
                    if (key[0] == 'cam'):
                        # This is a single camera and just the name
                        dbinfo.append('single')
                        camArrayTemp.append(key[1])
                    elif (key[0] == 'mon'):
                        # Get this monitor xbx info
                        myCursor.execute("Select lengthbywidthnum from configuredMonitors WHERE monitorName = '{0}';".format(key[1]))
                        thisMonInfo = str(myCursor.fetchone()[0])
                        
                        # Modify thisMonInfo so splits are unique, commas are NOT caught
                        dbinfo.append(thisMonInfo)
                        
                        # Get cameras to add to array from this mon
                        myCursor.execute("Select camarray from configuredMonitors WHERE monitorName = '{0}';".format(key[1]))
                        monCams = myCursor.fetchone()[0]
                        
                        for key, value in monCams.items():
                            # key is number, value is camera name
                            for key in value.keys():
                                # Add key (name) to temp array
                                camArrayTemp.append(key)
               
            # End of loops         
            # Write permenant camarray
            camarray = camArrayTemp    
            
            # Get delta
            myCursor.execute("Select timeinfo from configuredMonitors WHERE monitorName = '{0}';".format(monitor))
            delta = ((myCursor.fetchone()[0]).split('s'))[0]
            
        elif monList[1] == "map":
            monitorjsfile = "mapmode"
            myCursor.execute("Select camarray from configuredMonitors WHERE monitorName = '{0}';".format(monitor))
            # Set final CAMARRAY
            tmpArray = []
            camarray = (myCursor.fetchone()[0])

            for array in camarray:
                tmpArray.append(str(array))
                
            camarray = "|".join(tmpArray)

            # DBINFO is base64 of all maps
            myCursor.execute("Select mapname, image from mapData;")
            dbinfo = myCursor.fetchall()
            
            tmpArray = []
            
            for mapData in dbinfo:
                tmpArray.append(str(mapData))
                
            dbinfo = "|".join(tmpArray)
            
            
        return render_template('view_monitor.html', camarray=camarray, dbinfo=dbinfo, delta=delta, monitorjsfile=monitorjsfile, monitor=monitor, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.monitors", commit_id=commit_id, release_id=release_id)
# Will Allow FNAF Mode, single monitor mode, multi-monitor mode, premade views, true power!

    
# Grid editor
@app.route('/monitors/xbxedit/<monitor>', methods=['GET', 'POST'])
@login_required
def xbxedit(monitor):
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.monitors.xbxedit")):
        
        if request.method == 'POST':
            splitData = request.data.decode().split("|")
            lxw = splitData[0]
            timeinfo = splitData[1]
            camarray = splitData[2]
            # lengthbywidthnum, timeinfo, camarray

            # Position in array + 1 is slot index
            camarray = camarray.split(",")

            # Have processed data, now check if monitor entry exists, if not create new entry, if so modify entry.
            myCursor.execute("Select monitorName from configuredMonitors;")
            allMon = myCursor.fetchall()
                        
            # Create jsoncamarray
            
            jsoncamarray = {}
            
            for i, cam in enumerate(camarray):
                jsoncamarray[str(i + 1)] = {cam: {}}
                
            jsoncamarray = json.dumps(jsoncamarray)
            
            for mon in allMon:
                mon = str(mon)
                mon = mon[2:]
                mon = mon[:-3]
                
                if monitor == mon:
                    # Does exist! Modify DB entry
                    # TODO, camarray is currently array, need to make JSON nest using (array index + 1) as parent, then array data
                    # as child, then empty child for that.

                    myCursor.execute("UPDATE configuredMonitors SET lengthbywidthnum = %s, timeinfo = %s, camarray = %s WHERE monitorName = %s;", (lxw, timeinfo, (jsoncamarray,), monitor))
                    myDatabase.commit()
                    flash('Entry Modified')
                    return make_response(str("MODIFIED"), 200)
            
            # If the monitor exists then the above for loop will finish and return
            # If not, the below will run and return
            
            myCursor.execute("INSERT INTO configuredMonitors (lengthbywidthnum, timeinfo, camarray, monitorName, monitortemplate) VALUES (%s, %s, %s, %s, %s);", (lxw, timeinfo, (jsoncamarray,), monitor, "xbx"))
            myDatabase.commit()
            flash('Entry Created')
            return make_response(str("CREATED"), 200)
        # GET REQUEST
        # Two tabs, added monitors, add monitor, left would show all configured monitors in the db, while right would show templates
        # cameras and maps would be plugged into.
        
        # Proposed templates:
        # - X by X camera array, can scale, can be timed to roll to each.
        # - Single Camera Mode, with map at bottom right
        # - More later...
        # 'Templates' are just editors. Click on add new and brings up the specific new editor.
        
        loadedMonInfo = "False"
        # First, check if monitor exists, if not send false in loadedMonInfo, else send array.
        myCursor.execute("Select monitorName, monitortemplate from configuredMonitors;")
        allMon = myCursor.fetchall()
        
        myCursor.execute("Select name from localcameras ORDER BY name ASC")
        localcameras = myCursor.fetchall()
                                
        for mon in allMon:
            monitorName = str(mon[0])
            template = str(mon[1])
            
            if monitorName == monitor:
                # Make sure template is correct,
                if template == 'xbx':
                    # Load monitor info into var
                    # Loaded mon info would then be a tuple of the following:
                    # lengthbywidthnum, timeinfo, camarray
                        myCursor.execute("Select lengthbywidthnum, timeinfo, camarray from configuredMonitors WHERE monitorName = '{0}';".format(monitorName))
                        loadedMonInfo = myCursor.fetchall()
                        loadedMonInfo = str(loadedMonInfo).replace("', ", "'| ")
        
        
        return render_template('xbxarray_edit.html', localcameras=localcameras, loadedMonInfo=loadedMonInfo, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.monitors.xbxedit", commit_id=commit_id, release_id=release_id)

# Slideshow editor
@app.route('/monitors/slideshowedit/<monitor>', methods=['GET', 'POST'])
@login_required
def slideshowedit(monitor):
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.monitors.slideshowedit")):
        
        if request.method == 'POST':
            splitData = request.data.decode().split("|")
            timeinfo = splitData[0]
            disarray = splitData[1]
            disarray = disarray.split(",")
            # Create jsoncamarray for storage in db
            jsondisarray = {}
            
            for i, dis in enumerate(disarray):
                jsondisarray[str(i + 1)] = {dis: {}}
                
            jsondisarray = json.dumps(jsondisarray)
    
            # Have processed data, now check if monitor entry exists, if not create new entry, if so modify entry.
    
            myCursor.execute("Select monitorName from configuredMonitors;")
            allMon = myCursor.fetchall()
            
            for mon in allMon:
                mon = str(mon)
                mon = mon[2:]
                mon = mon[:-3]
                
                if monitor == mon:
                    # Does exist! Modify DB entry
                    myCursor.execute("UPDATE configuredMonitors SET timeinfo = %s, camarray = %s WHERE monitorName = %s;", (timeinfo, (jsondisarray,), monitor))
                    myDatabase.commit()
                    flash('Entry Modified')
                    return make_response(str("MODIFIED"), 200)
            
            # If the monitor exists then the above for loop will finish and return
            # If not, the below will run and return
            
            myCursor.execute("INSERT INTO configuredMonitors (timeinfo, camarray, monitorName, monitortemplate) VALUES (%s, %s, %s, %s);", (timeinfo, (jsondisarray,), monitor, "slideshow"))
            myDatabase.commit()
            flash('Entry Created')
            return make_response(str("CREATED"), 200)
    
        # GET REQUEST
        
        loadedMonInfo = "False"
        
        # Get all monitors for dropdown
        myCursor.execute("Select monitorName from configuredMonitors WHERE monitortemplate='xbx' ORDER BY monitorName ASC")
        xbxmon = myCursor.fetchall()
        
        # Get all cameras for dropdown
        myCursor.execute("Select name from localcameras ORDER BY name ASC")
        localcameras = myCursor.fetchall()
        
        # First, check if monitor exists, if not send false in loadedMonInfo, else send array.
        myCursor.execute("Select monitorName, monitortemplate from configuredMonitors;")
        allMon = myCursor.fetchall()
        
        # Check if exist, if so set loadedMonInfo to data                        
        for mon in allMon:
            monitorName = str(mon[0])
            template = str(mon[1])
            
            if monitorName == monitor:
                # Same name exists
                # Make sure template is correct,
                if template == 'slideshow':
                    # Is exist!
                    # Load monitor info into var
                    myCursor.execute("Select timeinfo, camarray from configuredMonitors WHERE monitorName = '{0}';".format(monitorName))
                    loadedMonInfo = myCursor.fetchall()
                    loadedMonInfo = str(loadedMonInfo).replace("', ", "'| ")
        
        
        return render_template('slideshow_edit.html', localcameras=localcameras, xbxmon=xbxmon, loadedMonInfo=loadedMonInfo, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.monitors.slideshowedit", commit_id=commit_id, release_id=release_id)

# Map monitor editor
@app.route('/monitors/mapmonedit/<monitor>', methods=['GET', 'POST'])
@login_required
def mapmonedit(monitor):
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.monitors.mapmonedit")):
        
        if request.method == 'POST':
            # Decode data
            mapCameraData = request.data.decode()
            mapCameraData = json.loads(mapCameraData)
            # Formalize data
            mapCameraData = json.dumps(mapCameraData)
            
            
            #mapCameraData is an array, should treat as such
            
            # Expected data format type
            # [["Floor1","Game Room",["Game Room",12.790697674418606,13.26530612244898],["Idol",12.956810631229235,78.31632653061224]],
            # ["Floor2","Test",["Idol",20.09966777408638,37.56177924217463],["Game Room",73.9202657807309,25.04118616144975]]]
            # Have processed data, now check if monitor entry exists, if not create new entry, if so modify entry.
    
            myCursor.execute("Select monitorName from configuredMonitors;")
            allMon = myCursor.fetchall()
            
            for mon in allMon:
                mon = str(mon)
                mon = mon[2:]
                mon = mon[:-3]
                
                if monitor == mon:
                    # Does exist! Modify DB entry
                    myCursor.execute("UPDATE configuredMonitors SET camarray = %s WHERE monitorName = %s;", ((mapCameraData,), monitor))
                    myDatabase.commit()
                    flash('Entry Modified')
                    return make_response(str("MODIFIED"), 200)
            
            # If the monitor exists then the above for loop will finish and return
            # If not, the below will run and return
            
            myCursor.execute("INSERT INTO configuredMonitors (camarray, monitorName, monitortemplate) VALUES (%s, %s, %s);", ((mapCameraData,), monitor, "map"))
            myDatabase.commit()
            flash('Entry Created')
            return make_response(str("CREATED"), 200)
            
        # GET REQUEST
        
        loadedMonInfo = "False"
        
        # First, check if monitor exists, if not send false in loadedMonInfo, else send array.
        myCursor.execute("Select monitorName, monitortemplate from configuredMonitors;")
        allMon = myCursor.fetchall()
        
        # Get all cameras for dropdown
        myCursor.execute("Select name from localcameras ORDER BY name ASC")
        localcameras = myCursor.fetchall()
        
        tmpLocal = []
        # Process for | split
        for cam in localcameras:
            # Clean up
            tmpLocal.append(cam[0])
        localcameras = "|".join(tmpLocal)
             
        # Fetch map names and map data, indexes corrolate
        myCursor.execute("Select mapname, image from mapData;")
        mapData = myCursor.fetchall()
        
        mapDataTemp = []
        
        for data in mapData:
            # For every entry in our database, reprocess for easier split later
            # Abstract to new array, keeps entries divided
            mapDataTemp.append(str(data))
            
        # Temp array constructed, reconstruct with | as entry seperator
        mapData = "|".join(mapDataTemp)
            
        # Check if exist, if so set loadedMonInfo to data                        
        for mon in allMon:
            monitorName = str(mon[0])
            template = str(mon[1])
            
            if monitorName == monitor:
                # Same name exists
                # Make sure template is correct,
                if template == 'map':
                    # Is exist!
                    # Load monitor info into var
                    myCursor.execute("Select camarray from configuredMonitors WHERE monitorName = '{0}';".format(monitorName))
                    loadedMonInfo = myCursor.fetchone()[0]
                                                            
                    tempArray = []
                    for data in loadedMonInfo:
                        tempArray.append(str(data))
                        
                    loadedMonInfo = "|".join(tempArray)
                      
        return render_template('map_edit.html', loadedMonInfo=loadedMonInfo, localcameras=localcameras, mapData=mapData, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.monitors.mapmonedit", commit_id=commit_id, release_id=release_id)


@app.route('/search/')
@login_required
def search():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.search")):
        # Return search.html with localcameras
        myCursor.execute("Select name from localcameras ORDER BY name ASC")
        localcameras = myCursor.fetchall()
        # Process for client
        tempArray = []
        for data in localcameras:
            tempArray.append(str(data[0]))
            
        localcameras = "|".join(tempArray) 
               
        return render_template('search.html', commit_id=commit_id, release_id=release_id, localcameras=localcameras)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.search", commit_id=commit_id, release_id=release_id)

# Will allow looking back at all available footage currently written to disk from the time called, lists date and time footage starts,
# allow selecting, highlighting, bookmarking, and exporting snapshots and mp4's. Will probably change how footage is wrote from mp4's
# to .ts livestream chunks and try to embed current system time into it. 
@app.route('/search/m3u8request', methods=['GET', 'POST'])
@login_required
def search_m3u8request():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.search")):
    
        if request.method == 'POST':
            requestData = json.loads(request.data.decode())
            camerasToRetrieve = requestData[0]
            
            # camerasToRetrieve is array of camera names, return data will be generated m3u8 with | as seperator
    
            # First we should parse the two dates into a python object
            fromDateObject = datetime.strptime(requestData[1], "%Y-%m-%dT%H:%M")
            toDateObject = datetime.strptime(requestData[2], "%Y-%m-%dT%H:%M")
            
            # Array to hold m3u8 strings
            m3u8StringArray = []
            
            print("From " + str(fromDateObject))
            print("To " + str(toDateObject))
            
            # Loop to generate m3u8 data
            
            for cameraNameSpace in camerasToRetrieve:
                # Future Check, does user have access to camera?
            
                urlList = []
                m3u8ObjectTextToSend = m3u8.M3U8()
                
                cameraName = cameraNameSpace.replace(" ", "-")
                # Open m3u8
                m3u8AbsolutePath = ('/zemond-storage/' + cameraName + '/' + cameraName + '.m3u8')
                m3u8PlaylistObject = m3u8.load(m3u8AbsolutePath)


                # Loop through each segment, check if is within date range, if so add url to urllist in order
                for segment in m3u8PlaylistObject.segments:
                    segmentDate = segment.program_date_time.replace(tzinfo=None)
                    if fromDateObject <= segmentDate <= toDateObject:
                        # print(segmentDate)
                        urlList.append(segment.uri)
                        # How do I get server address? Use stunServer, should always be this zemond box
                        baseFileName = (os.path.basename(segment.uri))
                        newUri = '/search/grabVideoFromStorage/' + cameraName + '/' + baseFileName
                        # Rewrite URI to reflect server and not local directory
                        segment.uri = newUri
                        segment.discontinuity = True
                        m3u8ObjectTextToSend.segments.append(segment)
                
                m3u8ObjectTextToSend.target_duration = 60
                m3u8ObjectTextToSend.media_sequence = 0
                m3u8ObjectTextToSend.playlist_type = 'VOD'
                m3u8ObjectTextToSend.version = 3
                m3u8ObjectTextToSend.is_endlist = True
                
                m3u8PlainText = m3u8ObjectTextToSend.dumps()
                
                # Add generated m3u8 to m3u8StringArray
                m3u8StringArray.append(m3u8PlainText)
                
            # Loop finished
            # Generate string response from array with | seperator
            m3u8ResponseString = "|".join(m3u8StringArray)
            
            return Response(m3u8ResponseString)
    else:
        return make_response("PERMISSION DENIED", 405)
    
# Get motion events for specific cameras, handles one camera at a time
@app.route('/search/grabMotionEventsBetweenTime', methods=['GET', 'POST'])
@login_required
def search_grabMotionEventsBetweenTime():
    if (auditUser(current_user.username, "permissionRoot.search")):
        if request.method == 'POST':
            # requestData 0, 1 is timefrom, timeto
            # requestData 2 is camera name
            requestData = json.loads(request.data.decode())
            camerasToRetrieve = requestData[0]
        # GET
    else:
        return make_response("PERMISSION DENIED", 405)
    
@app.route('/search/grabVideoFromStorage/<cameraName>/<videoFileName>', methods=['GET', 'POST'])
@login_required
def search_grabVideoFromStorage(cameraName, videoFileName):
    if (auditUser(current_user.username, "permissionRoot.search")):
        try:
            # FUTURE CHECK, does user have access to camera?
            if '.ts' in videoFileName:
                fileNameDiskUri = ('/zemond-storage/' + cameraName + '/' + videoFileName)
                return send_file(fileNameDiskUri, mimetype='video/MP2T', as_attachment=False, conditional=True)
            else:
                return make_response("REQUEST NOT FOR TS FILE", 404)
        except Exception as e:
            return make_response("404 FILE NOT FOUND", 404)
    else:
        return make_response("PERMISSION DENIED", 405)
    
@app.route('/cameralist/')
@login_required
def cameraList():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.camera_list")):   
        global snapshotCache
        
        # Get all added cameras, put into tupple.
        myCursor.execute("Select * from localcameras ORDER BY name ASC")
        localcameras = myCursor.fetchall()
        
        # Get camera model details, and reference pic.
        myCursor.execute("Select * from cameradb")
        cameradb = myCursor.fetchall()
        
        # Get all cameras user is allowed to access
        myCursor.execute("Select camPermissions from userTable WHERE username='{0}'".format(current_user.username))
        camPerms = myCursor.fetchall()
        camPermsSplit = camPerms[0][0]

        # Data structure to send: Snapshot, Camera Name, Model & Serial, Camera Image

        # To process: Get All From Local Cameras, associate with model number, using that 'add' data to the tuple
        dataToSend = None;
        sendCameraList = []
                
        # First check if user can access it
        for row in localcameras:
            try:
                for cam in camPermsSplit:
                    if cam == row[0]:
                        # print("Matches")
                        sendCameraList.append(row)
                        break
                    else:
                        # print("Does not match: " + str(row))
                        isMatch = False
            except Exception as e:
                print("No Camera Permissions Found! " + str(e))    
                pass
            
        # For every camera pulled, add it to the table we send to the client.
        for row in sendCameraList:
            
            # Get Current Name
            currentiname = row[0]

            # Create httpurl
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

            # Create Info String For Manufacturer Model

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
        if dataToSend == None:
            dataToSend = (("", "No Camera's Added!", "", "", "", ""), )
            
        return render_template('cameralist.html', data=dataToSend, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.camera_list", commit_id=commit_id, release_id=release_id)

@app.route('/settings/')
@login_required
def settings():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings")):   
        return render_template('settings.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings", commit_id=commit_id, release_id=release_id)

# Mod User Permissons
@app.route('/settings/manage_perms/', methods=['GET', 'POST'])
@login_required
def manage_perms():
    if (auditUser(current_user.username, "permissionRoot.settings.manage_perms")):   
        if request.method == 'POST':
            # Check command
            requestSplit = request.data.decode().split(':')
            print(requestSplit)
            command = requestSplit[0]
            if command == 'getPermissions':
                # Change user logic
                data = requestSplit[1]
                myCursor.execute("Select permissions,camPermissions from userTable WHERE username='{0}'".format(data))
                combPerm = myCursor.fetchall()                

                
                return make_response(str(combPerm), 200)
            
            elif command == 'addPerm':
                reqPerm = requestSplit[1]
                user = requestSplit[2]
                # Check if PERM already exists
                myCursor.execute("Select permissions from userTable WHERE username='{0}'".format(user))
                perms = str(myCursor.fetchall())
                perms = perms[3:len(perms) - 4]
                perms = perms.replace("'", "")
                perms = perms.split(', ')

                for perm in perms:
                    if reqPerm == perm:
                        print(perm)
                        return make_response(str("FALSE"), 200)
                                 
                # If not have perm, allow to happen and send audit log
                sendAuditLog(current_user.username, "HIGH", "Added Permission " + reqPerm + " to user " + user)
                
                # UPDATE userTable SET permissions = ARRAY_APPEND(permissions, '{0}') WHERE username = {1};
                myCursor.execute("UPDATE userTable SET permissions = ARRAY_APPEND(permissions, '{0}') WHERE username = '{1}';".format(reqPerm, user))
                myDatabase.commit()
                
                return make_response(str("TRUE"), 200)
            
            elif command == 'rmPerm':
                # Try to remove from DB, if fails because it dosen't exist then that's a client issue.
                    reqPerm = requestSplit[1]
                    user = requestSplit[2]
                    try:
                        myCursor.execute("UPDATE userTable SET permissions = ARRAY_REMOVE(permissions, '{0}') WHERE username = '{1}';".format(reqPerm, user))
                        myDatabase.commit()
                        # Send audit log
                        sendAuditLog(current_user.username, "HIGH", "Removed Permission " + reqPerm + " from user " + user)
                        return make_response(str("TRUE"), 200)
                    except:
                        return make_response(str("FALSE"), 200) 
        
            elif command == 'addCam':
                reqCam = requestSplit[1]
                user = requestSplit[2]
                # Check if CAM already exists
                myCursor.execute("Select campermissions from userTable WHERE username='{0}'".format(user))
                cams = str(myCursor.fetchall())
                cams = cams[3:len(cams) - 4]
                cams = cams.replace("'", "")
                cams = cams.split(', ')

                for cam in cams:
                    if reqCam == cam:
                        # print(cam)
                        return make_response(str("FALSE"), 200)
                                 
                # If not have perm, allow to happen and send audit log
                sendAuditLog(current_user.username, "HIGH", "Added Camera " + reqCam + " to user " + user)
                
                # UPDATE userTable SET permissions = ARRAY_APPEND(permissions, '{0}') WHERE username = {1};
                myCursor.execute("UPDATE userTable SET campermissions = ARRAY_APPEND(campermissions, '{0}') WHERE username = '{1}';".format(reqCam, user))
                myDatabase.commit()
                
                return make_response(str("TRUE"), 200)   
            
            elif command == 'rmCam':
                # Try to remove from DB, if fails because it dosen't exist then that's a client issue.
                reqCam = requestSplit[1]
                user = requestSplit[2]
                try:
                    myCursor.execute("UPDATE userTable SET campermissions = ARRAY_REMOVE(campermissions, '{0}') WHERE username = '{1}';".format(reqCam, user))
                    myDatabase.commit()
                    # Send audit log
                    sendAuditLog(current_user.username, "HIGH", "Removed Camera " + reqCam + " from user " + user)
                    return make_response(str("TRUE"), 200)
                except:
                    return make_response(str("FALSE"), 200) 
    
    #####
    ##GET
    #####
                
        # Grab user list of users, when one is selected get user perms and camperms, and allow modification
        myCursor.execute("SELECT DISTINCT username FROM userTable ORDER BY username ASC;")
        userList = myCursor.fetchall()
        
        # Remove current user from userlist
        for user in userList:
            if current_user.username == user[0]:
                userList.remove(user)
        
        # Grab all local cameras
        myCursor.execute("SELECT DISTINCT name FROM localcameras ORDER BY name ASC;")
        camList = myCursor.fetchall()
        
        session.pop('_flashes', None)
        return render_template('permission_mod.html', camList=camList, permissionTreeObject=permissionTreeObject, userlist=userList, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.manage_perms", commit_id=commit_id, release_id=release_id)

# Sync users in ldap, do later.
@app.route('/settings/sync_ldap/', methods=['GET', 'POST'])
@login_required
def syncLdap():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.sync_ldap")):   
        return render_template('inProgress.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.sync_ldap", commit_id=commit_id, release_id=release_id)

# Audit log view
@app.route('/settings/audit_log/', methods=['GET', 'POST'])
@login_required
def auditLog():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.audit_log")):
        
        myCursor.execute('SELECT * FROM auditLog ORDER BY timelogged DESC;')
        logs = myCursor.fetchall()
           
        # Add sorting and CSV export later, for now it can happen through direct DB export.
           
        return render_template('audit_log.html', logs=logs, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.sync_ldap", commit_id=commit_id, release_id=release_id)


# When adding a user manually, do it here
@app.route('/settings/add_user/', methods=['GET', 'POST'])
@login_required
def addUser():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.add_user")):   
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            if not username:
                session.pop('_flashes', None)
                flash('Username is required!')
            elif not password:
                session.pop('_flashes', None)
                flash('Password is required!')
            else:
                didGetUser = createUser(username, password)
                if didGetUser:
                    session.pop('_flashes', None)
                    flash('User created!')
                elif not didGetUser:
                    session.pop('_flashes', None)
                    reset_pass_link = Markup('<a href="' + url_for('resetPassword') + '">reset password instead?</a>')
                    flash('User exists, ' + reset_pass_link)

        return render_template('add_user.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.add_user", commit_id=commit_id, release_id=release_id)

# If a user needs a password reset
@app.route('/settings/reset_password/', methods=['GET', 'POST'])
@login_required
def resetPassword():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.reset_password")):   
        if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                if not username:
                    session.pop('_flashes', None)
                    flash('Username is required!')
                elif not password:
                    session.pop('_flashes', None)
                    flash('Password is required!')
                else:
                    # Check if user exists... if so 
                    userExists = verifyDbUser(username)
                    if userExists:
                        # Privlige check, auditUser.userPassword.reset(username) Get True Or False based on if has privledge
                        # Implement eventually
                        resetUserPass(username, password)
                        session.pop('_flashes', None)
                        flash('User password reset.')
                    else:
                        session.pop('_flashes', None)
                        flash('User does not exist.')

        return render_template('reset_password.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.reset_password", commit_id=commit_id, release_id=release_id)

# User delete requested, route here
@app.route('/settings/delete_user/', methods=['GET', 'POST'])
@login_required
def deleteUser():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.delete_user")):   
        sessionUsername = current_user.username
        if request.method == 'POST':
            postpassword = request.form['postpassword']
            # Get User Password, verify user, verify permissions, delete user.
            #audit
            
            myCursor.execute("Select password from userTable WHERE username='{0}'".format(sessionUsername))
            dbPass = myCursor.fetchone()
            currentDbPass = ''.join(dbPass)
            # Originally wanted to hash submitted password and check if it matches with what's in DB,
            # but cryptocode generates a different Hash :/
            # Now I just decrypt the DB entry and compare.
        
            if postpassword == cryptocode.decrypt(str(currentDbPass), passwordRandomKey):
                # User entered password, now verify del user exists and del
                if verifyUserPassword(current_user.username, postpassword):
                    # Now delete the DB entry of the cameraName
                    myCursor.execute("DELETE FROM userTable where username='{0}'".format(sessionUsername))
                    myDatabase.commit()


        # Get all camera's
        myCursor.execute("Select name from localcameras")
        camnames = myCursor.fetchall()

        # Generate user list from userTable
        myCursor.execute("Select username from userTable;")
        dbList = myCursor.fetchall()
        
        userList = []
        
        for user in dbList:
            if user[0] != sessionUsername:
                userList.append(user[0])
            
        return render_template('delete_user.html', userList=userList, commit_id=commit_id, release_id=release_id)  
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.delete_user", commit_id=commit_id, release_id=release_id)


# This one is automatic
@app.route('/settings/add_camera/', methods=['GET', 'POST'])
@login_required
def addCamera():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.add_camera")):   
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
                    # A Un-Parseable response if ONVIF is not supported, 200 If it is with what's expected from GetDeviceInfomation

                    # Send GetDeviceInfomation and determine action.

                    try:
                        response = sendONVIFRequest(GetDeviceInformation, onvifURL, username, password)
                    except Exception as e:
                            # Camera does not support onvif!
                            session.pop('_flashes', None)
                            flash('Camera does not seem to support Onvif, the following exception was raised: ' + str(e))
                    else:

                        parsedResponseXML = BeautifulSoup(response.text, 'xml')

                        # print(response.text)

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
                                
                                    addRunningContainer(cameraname, rtspCredString, "1")
                                    return redirect(url_for('dashboard'))

        return render_template('add_camera.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.add_camera", commit_id=commit_id, release_id=release_id)

# Manual, if having to use non-ONVIF RTSP video sources
@app.route('/settings/add_camera_manual/', methods=['GET', 'POST'])
@login_required
def addCameraManual():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.add_camera_manual")):   
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
        return render_template('add_camera_manual.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.add_camera_manual", commit_id=commit_id, release_id=release_id)

# List all camera models gathered over time
@app.route('/settings/camera_models/', methods=['GET', 'POST'])
@login_required
def cameraModels():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.camera_models")):   
        if request.method == 'POST':
            if 'cameraimage' not in request.files:
                return 'cameraimage not in form!'
            selectedModel = request.form['submit_button']
            imageFile = request.files['cameraimage'].read()
            imageb64 = str(base64.b64encode(imageFile).decode("utf-8"))
            # Should be data:image/png;base64,iVBORw0KGgo
            myCursor.execute("UPDATE cameradb SET image=(%s) WHERE model = '{0}'".format(selectedModel), (imageb64, ))
            myDatabase.commit()

        myCursor.execute("Select * from cameradb;")
        cameradb = myCursor.fetchall()
        return render_template('camera_models.html', data=cameradb, commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.camera_models", commit_id=commit_id, release_id=release_id)

# Return Favicon
@app.route('/favicon.ico')
def returnIcon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                          'pictures/logo.png',mimetype='image/vnd.microsoft.icon')

# View a camera, using WebRTC, and ONVIF Event Logs, with Recording Information and quick view, plus a link to the camera.
# UUID Will be tied to the user, and hopefully when I pull the UUID from userUUIDAssociations watchdog will catch it and shut everything down.
@app.route('/view_camera/<cam>', methods=['GET', 'POST'])
@login_required
def viewCamera(cam):
    session.pop('_flashes', None)
    # Permission works different here, we assume everything after view_camera is the cam name, so we run that seperate, as that would be
    # camPermissions, every cam as a different array string
    if ((auditUser(current_user.username, "permissionRoot.camera_list.view_camera")) and (cameraPermission(current_user.username, str(cam)))):   
        global player

        # To view the camera, we need to custom make the data we are going to pass over, like in the Camera List. Formatted as follows:
        # Name, Manufacturer, Model Number, Serial, Firmware, CameraImage, IP. 
        
        # Generate Static Data
        myCursor.execute("Select * from localcameras where name = '{0}' ".format(cam))
        camtuple = myCursor.fetchall()
        camdata = camtuple[0]
        # Currently passing through the raw DB query.
        cameraModel = camdata[7]
        
        # Get hasTWA from DB and see if we can start webRtc immediently or have to show audio warning
        myCursor.execute("Select hastwa from cameradb where model = '{0}' ".format(cameraModel))
        hasTwa = myCursor.fetchone()
        
        # Both the client and server implement 'RTCRemotePeer' and can exchange SDP with HTTP POST. Use that SDP with the Peer and you
        # Have a remote WebRTC Peer you can send video to! All processing and reconstruction is done on the client side.

        # SDP is published to /rtcoffer/<cam>

        # First we need to generate the raw datastream from the RTSP URL, we'll call another thread to do this, as it's temporary.
        # This updates the frames to pass to webrtc

        # We need to pass through a custom data string now, with Onvif Events as seperate string, both as follows:
        # GeneralData: Camera Name | Manufacturer | Model | Serial | IP Address | Camera Model Picture
        # 
        # Onvif Events: Time | Topic | Data
        # Get Onvif Events:

        myCursor.execute("Select * from cameraevents where name = '{0}' AND messagetime >= now() - INTERVAL '7 days' ORDER BY messagetime DESC;".format(cam))
        rawOnvifQuery = myCursor.fetchall()

        return render_template('view_camera.html', data=camdata, onvifevents=rawOnvifQuery, commit_id=commit_id, release_id=release_id, hasTWA=hasTwa[0])  
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.camera_list.view_camera, {0}".format(cam), commit_id=commit_id, release_id=release_id)

# WEBRTC ===================================
# When we grab a WebRTC offer from out browser client for single camera.
@app.route('/rtcoffer/<cam>', methods=['GET', 'POST'])
@login_required
def webRTCOFFER(cam):
    thisUUID = str(uuid.uuid4()) # Generate a UUID for this session.
    
    # Get current user (Static currently)
    thisUser = current_user.username
    
    global webRTCThread

    # Get Docker IP
    # Get Name's Docker IP with username and password
    myCursor.execute("Select dockerIP from localcameras where name='{0}'".format(cam))
    dockerIP = myCursor.fetchone()
    dockerIPString = ''.join(dockerIP)

    # Always create a new event loop for this session.
    rtcloop = asyncio.new_event_loop()
    
    # Add generated info to userUUIDAssociation
    # UUID, user[0], pingtime[1], rtcloopObject[2], userInTrackControl[3], camName[4], rtcPeer[5], dataChannel[6], microphoneStreamFuture[7] (7 appended)
    # MODIFY SO 5 BECOMES the WEBRTC PEER and 6 is MICROPHONE
    userUUIDAssociations[thisUUID] = [thisUser, 0, rtcloop, False, cam]

    # Get SDP from client and set set objects
    parsedSDP = userUUIDAssociations[thisUUID][2].run_until_complete(singleWebRtcStart(thisUUID, dockerIPString, cam, request))
        
    # Continue running that loop forever to keep AioRTC Objects In Memory Executing, while shifting it to
    # Another thread so we don't block the code.
    # webRTCThread = Thread(target=userUUIDAssociations[thisUUID][2].run_forever)
    webRTCThread = Thread(target=userUUIDAssociations[thisUUID][2].run_until_complete, args=(rtcWatchdog(thisUUID), ))
    webRTCThread.start()
    
    # Return Our Parsed SDP to the client
    return parsedSDP.encode()

# Offer for monitors
@app.route('/monitors/offer/<monitor>', methods=['GET', 'POST'])
@login_required
def offer_monitor(monitor):
    thisUUID = str(uuid.uuid4()) # Generate a UUID for this session.
    
    # Get current user (Static currently)
    thisUser = current_user.username
    
    # Get WebRTCThread
    global webRTCThread
    
    # Final array object
    formatCamArray = []
    
    # Get the assigned camarray from the monitor.
    myCursor.execute("Select camarray, monitortemplate from configuredMonitors WHERE monitorName = '{0}';".format(monitor))
    data = myCursor.fetchone()
    camarray = data[0]
    monType = data[1]
    
    # Convert camarray json to camarray array for easy processing.
    try:
        for key, value in camarray.items():
            formatCamArray.append(list(value.keys())[0])
    except:
        pass
        
    # Now that we have the formatted array, determine the template

    finalFormatArray = []

    # Need to modify our formatCamArray so instead of monitor names, we exand it to all the camera names in the monitor
    if (monType == 'slideshow'):
        for entry in formatCamArray:
            entry = entry.split(':')
            if entry[0] == 'cam':
                finalFormatArray.append(entry[1])
            elif entry[0] == 'mon':
                # Get all camera entries for monitor and write those to finalFormatArray
                myCursor.execute("Select camarray from configuredMonitors WHERE monitorName = '{0}';".format(entry[1]))
                monCams = myCursor.fetchone()[0]
                
                for key, value in monCams.items():
                    for key in value.keys():
                        # Have camera name, add to finalFormatArray
                        finalFormatArray.append(key)
        formatCamArray = finalFormatArray    
        
    elif (monType == 'map'):
        # Attempt to reconruct client slide camNameArray
        
        for floorArray in camarray:
            trackVar = 0;
            
            # Loop over each button array
            for buttonArray in floorArray:
                doesExist = False
                
                # Not actually a buttonArray unless trackVar is above 1
                if trackVar > 1:
                    buttonCameraName = (floorArray[trackVar])[0];
                    
                    # Check if buttonCameraName is already in formatCamArray,                     
                    for camName in formatCamArray:
                        # If equals, then doesExist is true
                        if camName == buttonCameraName:
                            doesExist = True
                    
                    
                    # Check has been processed, if not doesExist then add to array
                    
                    if doesExist == False:
                        formatCamArray.append(buttonCameraName)
                    
                # floorArray Tracker
                trackVar = trackVar + 1;

    # Format cam array for SQL statement
    camnames = ', '.join(f"'{cam}'" for cam in formatCamArray)
    # PSQL statement to get all dockerIPs from my list
    # From Phind again, actual magic.
    # FROM line creates a new table from the camnames array, holding the position with ORIDNALITY
    # JOIN line joins the table with localcameras name sorting.
    # ORDER line returns the table to output.
    myCursor.execute(f"""SELECT l.dockerIP
    FROM unnest(ARRAY[{camnames}]) WITH ORDINALITY AS n(name, ord) 
    JOIN localcameras l ON l.name = n.name
    ORDER BY n.ord;""")
    # assign ip array from response
    dockerIpArray = [row[0] for row in myCursor.fetchall()]
            
    # Create a new event loop for this session. Allows for us to continue code, but also get a response from the client sdp
    rtcloop = asyncio.new_event_loop()
        
    # An SSRC is a 'Synchronization Source' for WebRTC Transceivers to properly route RTP streams, ONLY UNIQUE IDENTIFIER FOR ASSOCIATING STREAMS
    # SSRC Associate variable so we can assign unique video stream to ssrc (random32 integer)
    # Associated via index, so formatCamAray[3] would be equal to ssrcAssoc[3]
    ssrcAssoc = []
        
    # # # Now create a timer that is reset by Ping-Pong.
    # Add generated info to userUUIDAssociation
    # UUID, user[0], pingtime[1], rtcloopObject[2], userInTrackControl[3], camName[4], webRtcPeer[5], rtcDataChannel[6], microphoneStreamFuture[7] (7 appended)
    userUUIDAssociations[thisUUID] = [thisUser, 0, rtcloop, False, monitor]

    # Get parsed SDP from monWebRTC which creates all the monitor players from dockerIpArray
    parsedSDP = userUUIDAssociations[thisUUID][2].run_until_complete(monWebRtcStart(request, thisUUID, dockerIpArray, formatCamArray, ssrcAssoc))
    
    # Need to combine return SDP and ssrcAssoc into one piece of returnable data for monitor to use (Done already in monWebRtcStart)
    # I question everyday why WebRTC is the way it is, no wonder the existing tutorials are so lacking and soulless
        
    # # Continue running that loop forever to keep AioRTC Objects In Memory Executing, while shifting it to
    # # Another thread so we don't block the code.
    # webRTCThread = Thread(target=rtcloop.run_forever)
    webRTCThread = Thread(target=userUUIDAssociations[thisUUID][2].run_until_complete, args=(rtcWatchdog(thisUUID), ))
    webRTCThread.start()
      
    # # # Return Our Parsed SDP to the client
    return parsedSDP.encode()
# WEBRTC END ===================================

@app.route('/settings/delete_camera/', methods=['GET', 'POST'])
@login_required
def deleteCamera():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.settings.delete_camera")):   
        if request.method == 'POST':
            campass = request.form['campass']
            postpassword = request.form['userpass']
            cameraName = request.form['camname']
            # This post request will only run if both of these values not only
            # First check Camera Password Against Server, pull from DB
            # Then get current user ID, and password hash, then compare!

            # Get Campass From DB
            myCursor.execute("Select password from localcameras where name='{0}'".format(cameraName))
            currentpassword = myCursor.fetchone()
            currentpasswordString = ''.join(currentpassword)
            # Originally wanted to hash submitted password and check if it matches with what's in DB,
            # but cryptocode generates a different Hash :/
            # Now I just decrypt the DB entry and compare.
            decryptedDBPASS =  cryptocode.decrypt(str(currentpasswordString), passwordRandomKey)

            if campass == decryptedDBPASS:
                # Now check if the user password matches
                if verifyUserPassword(current_user.username, postpassword):
                    # Now delete the DB entry of the cameraName
                    myCursor.execute("DELETE FROM localcameras where name='{0}'".format(cameraName))
                    myDatabase.commit()
                    # Now that the DB entry is gone, remove the Docker Container!
                    removeContainerCompletely(cameraName)


        # We will give a text based list of the camera names, when a camera is clicked on, you will need your Users password for zemond
        # and the camera's password on file.

        # Get all camera's
        myCursor.execute("Select name from localcameras")
        camnames = myCursor.fetchall()

        return render_template('delete_camera.html', data=camnames, commit_id=commit_id, release_id=release_id)  
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.settings.delete_camera", commit_id=commit_id, release_id=release_id)

def loopWatchdogThread():
    global userUUIDAssociations
    # Thread to check every second if rtc uuid still exists if not close rtc loop and stop.
    # Code will fail as loop itterator changes size often, 
    while sigint == False:
        time.sleep(1)
        
        try:
            for uuid in userUUIDAssociations:    
                if userUUIDAssociations[uuid][2].is_running() == False:
                    # Close event loop to close threads
                    userUUIDAssociations[uuid][2].close()
                    
                    # Remove from userUUIDAssociations
                    del userUUIDAssociations[uuid]
        except:
            pass
        
        # Do variable updates, doing here so I don't have to open another thread.
        # Variables to show on Dashboard.
        # Amount of threads and threads open:
        
        globalFunctions.threadsRunning = str(active_count())
        
        # Empty array
        globalFunctions.threadsArray = []
        # Itterate over array
        for thread in threading.enumerate():
            # strToDe = (str(thread.name) + " | " + str(thread._target)) 
            globalFunctions.threadsArray.append(str(thread.name))
            
        # System CPU
        globalFunctions.systemCpu = str(psutil.cpu_percent()) + "%"
        
        # System Memory
        globalFunctions.systemMem = str(psutil.virtual_memory().percent) + "%"
        
        # User sessions
        globalFunctions.sessionsArray = []
        for sessionUUID in userUUIDAssociations:
        # UUID, user[0], pingtime[1], rtcloopObject[2], userInTrackControl[3], camName[4],
        # webRtcPeer[5], rtcDataChannel[6], microphoneStreamFuture[7] (7 appended)
            
            stringToPush = (str(userUUIDAssociations[sessionUUID][0]) + " | " + 
                            str(userUUIDAssociations[sessionUUID][4]) + " | Has Control: " + 
                            str(userUUIDAssociations[sessionUUID][3]))
            
            globalFunctions.sessionsArray.append(stringToPush)
            
def updateSnapshots():
    # Update the snapshots in the camera list
    while True:
        try:
            if sigint == False:
                # This runs infinitly in another thread at program start,
                # this gets a list of all the cameras, creates a string for each of them, (A Dictionary), then gets
                # a snapshot of it, and stores it. They can be called anytime.

                myCursor.execute("Select * from localcameras")
                localcameras = myCursor.fetchall()

                global snapshotCache
                global onlineCameraCache
                # Reset Temp Cache

                tempCache = {}
                tmpCameraCache = 0

                for row in localcameras:
                    # Get Current Name
                    currentiname = row[0]
                    # Get Current IP
                    dockerIP = row[10]
                    # First Generate Snapshot, from docker container
                
                    # Assemble Credential Based RTSP URL
                    dockerRtspUrl = ("rtsp://" + dockerIP + ":8554/cam1")
                    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'
                    cap = cv2.VideoCapture(dockerRtspUrl)

                    if not cap.isOpened():
                        # print('Cannot open RTSP stream')
                        # Assuming that docker container isn't started, just break the loop then try again.
                        break
                    else:
                        readquestion, frame = cap.read()
                        # print("Got Snapshot for " + currentiname)
                        # This means the camera is online, to put it simply. Add this to a counter.
                        tmpCameraCache = tmpCameraCache + 1
                        cap.release()

                    try:
                        _, im_arr = cv2.imencode('.jpg', frame)  # im_arr: image in Numpy one-dim array format.
                    except:
                        break
                    im_bytes = im_arr.tobytes()
                    im_b64 = base64.b64encode(im_bytes).decode("utf-8") # Base 64 Snapshot

                    # Add data to dictionary as Name : IMG
                    tempCache[currentiname]=im_b64

                snapshotCache = tempCache; # When temp Cache is finished filling, finalize it.
                onlineCameraCache = tmpCameraCache;
                time.sleep(15) # Time to wait between gathering snapshots
            else:
                break;
        except:
            pass

def startWebClient():
    # Testing Web Server
    # app.run(host='0.0.0.0')

    # Production web server
    print("Web Client Started.")
    serve(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    # For when needed
    # tracemalloc.start()
    
    os.environ['PYAV_LOGGING'] = 'off'
    
    logger = logging.getLogger('asyncio')
    logger.setLevel(logging.ERROR)
    
    setCommitID()
    
    dockerComposer.firstRunDockerCheck = False

    # Start Docker Management Thread, which checks the localcameras table and using that determines if all docker containers are runnning.
    dockerThread = Thread(target=dockerWatcher)
    dockerThread.start()
    
    # Start loop watcher thread, if one is stopped, close it!
    loopWatchdogThreaden = Thread(target=loopWatchdogThread)
    loopWatchdogThreaden.start()
    
    # Start rest of program after docker containers start
    
    while (dockerComposer.firstRunDockerCheck == False):
        # print("Docker check failed, waiting 5 seconds to check again.")
        time.sleep(5)

    if (dockerComposer.firstRunDockerCheck == True):
        print("Docker check True! Start Web Interface in 5 seconds")
        # Start Snapshot Thread.
        snapshotThread = Thread(target=updateSnapshots)
        snapshotThread.start()
        
        # Register SIGINT Handler
        signal.signal(signal.SIGINT, sigint_handler)
        
        # Wait 5 seconds
        time.sleep(5)
        startWebClient()