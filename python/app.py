import cryptocode, av, websockets, time, ast, logging, cv2, sys, os, psycopg2, argparse, asyncio, json, logging, ssl, uuid, base64, queue, dockerComposer # Have to import for just firstRun because of global weirdness
from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory, Markup, make_response
from flask_sock import Sock
from flask_login import LoginManager, UserMixin, login_user, current_user
from functools import wraps
from bs4 import BeautifulSoup
from io import BytesIO
from threading import Thread, active_count
from git import Repo
from waitress import serve # Production server

# COMMENT TO SEE FFMPEG OUTPUT, OR ADD TRACE
os.environ['AV_LOG_LEVEL'] = 'quiet'
# WebRTC
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer, RTCDataChannel
from aiortc.contrib.media import MediaPlayer, MediaRelay, MediaBlackhole
from aiortc.rtcrtpsender import RTCRtpSender

#import Zemond Specific Parts
from onvifRequests import *
from onvifAutoConfig import onvifAutoconfigure
from globalFunctions import passwordRandomKey, myCursor, myDatabase, sendONVIFRequest
from dockerComposer import addRunningContainer, dockerWatcher, removeContainerCompletely, firstRunDockerCheck
from ptzHandler import readPTZCoords, sendContMovCommand
from twoWayAudio import streamBufferToRemote
from userManagement import createUser, verifyDbUser, resetUserPass, verifyUserPassword, auditUser, cameraPermission, sendAuditLog
from permissionTree import permissionTreeObject

app = Flask(__name__)
login_manager = LoginManager(app)
login_manager.init_app(app)

app.secret_key = 'IShouldBeUnique!' # Change this, as it's just good practice, generate some random hash string.

app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
)

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

global snapshotCache, userUUIDAssociations;

userUUIDAssociations = {}

release_id = 'Alpha 0.0.1'

commit_id = ''

# ONVIF URL STANDARD: http(s)://ip.address/onvif/device_serivce 

def setCommitID():
    global commit_id
    repo = Repo("./")
    commit_id = repo.head.commit.hexsha
    commit_id = commit_id[:10] + "..."

# If not logged_in, make em!
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        # print(str(session))
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login first.')
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
    if request.method == 'POST':
        inputtedUsername = request.form['username']
        if (auditUser(inputtedUsername, "permissionRoot.userSettings.accountActive")):
            # Check if username exists in database
            # DO HERE incase somebody is bruteforcing logins with different names, real or not.
            if verifyUserPassword(inputtedUsername, request.form['password']):
                
                                
                localUserObject = User(inputtedUsername)
                # Register user with flask session by passing in username as string, and it makes it a user object same character set as string
                # "user" --> user (as instance of User())
                login_user(localUserObject)
                # Set logged_in to true so can access any page
                session['logged_in'] = True
                session.pop('_flashes', None)
                flash('Your logged in!')
                return redirect(url_for('index'))
            else:
                session.pop('_flashes', None)
                flash('Username or Password is incorrect!')
        else:
            session.pop('_flashes', None)
            flash('Account Inactive')
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
        return render_template('dashboard.html', camerasonline=onlineCameraCache, offlineCamNum=offlineCamNum, commit_id=commit_id, release_id=release_id) #onlineCameraCache current amount of cameras
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.dashboard", commit_id=commit_id, release_id=release_id)

@app.route('/monitors/')
@login_required
def monitors():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.monitors")):
        return render_template('inProgress.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.monitors", commit_id=commit_id, release_id=release_id)
# Will Allow FNAF Mode, single monitor mode, multi-monitor mode, premade views, true power!

@app.route('/search/')
@login_required
def search():
    session.pop('_flashes', None)
    if (auditUser(current_user.username, "permissionRoot.search")):    
        return render_template('inProgress.html', commit_id=commit_id, release_id=release_id)
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.search", commit_id=commit_id, release_id=release_id)
# Will allow looking back at all available footage currently written to disk from the time called, lists date and time footage starts,
# allow selecting, highlighting, bookmarking, and exporting snapshots and mp4's. Will probably change how footage is wrote from mp4's
# to .ts livestream chunks and try to embed current system time into it. 

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
                                
                                    addRunningContainer(cameraname, rtspCredString, "268435456", "48")
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
    
        # Both the client and server implement 'RTCRemotePeer' and can exchange SDP with HTTP POST. Use that SDP with the Peer and you
        # Have a remote WebRTC Peer you can send video to! All processing and reconstruction is done on the client side.

        # SDP is published to /rtcoffer/<cam>

        # First we need to generate the raw datastream from the RTSP URL, we'll call another thread to do this, as it's temporary.
        # This writes a frame to the POST url buffer and consistantly updates it, 

        # We need to pass through a custom data string now, with Onvif Events as seperate string, both as follows:
        # GeneralData: Camera Name | Manufacturer | Model | Serial | IP Address | Camera Model Picture
        # 
        # Onvif Events: Time | Topic | Data
        # Get Onvif Events:

        myCursor.execute("Select * from cameraevents where name = '{0}' ORDER BY messagetime DESC".format(cam))
        rawOnvifQuery = myCursor.fetchall()

        return render_template('view_camera.html', data=camdata, onvifevents=rawOnvifQuery, commit_id=commit_id, release_id=release_id)  
    else:
        return render_template('permission_denied.html', permissionString="permissionRoot.camera_list.view_camera, {0}".format(cam), commit_id=commit_id, release_id=release_id)

# WEBRTC ===================================
#
def uuidWatchdog():
    # Make a regular thread that checks all added UUIDS, and the pingtime attatched.
    # If pingtime is above set value, stop and close.
    global userUUIDAssociations
    
    while True:
        # Check every second
        time.sleep(1)
        # print(userUUIDAssociations)

        # Loop through each UUID and check Pingtime
        for uuid in userUUIDAssociations:
            # print("Check UUID: " + uuid)
            iPingtime = userUUIDAssociations[uuid][1]
            # print("Found Pingtime: " + str(iPingtime))
            diffTime = float(time.time()) - float(iPingtime)
            # print("Diff time:" + str(diffTime))
            
            if (diffTime > 5.0 and iPingtime > 0):
                iLoop = userUUIDAssociations[uuid][2]
                print("Running Threads Before: " + str(active_count()))
                iLoop.stop() # This tells the Event Loop to stop executing code, but it does not CLOSE the loop! (Which leaves 1 cascading thread!)
                time.sleep(3) # Wait three seconds for code to stop executing...
                iLoop.close() #  Close event loop, which reduces thread count back to what it was originally. <---- THIS WAS A BIG FIX
                print("Running Threads After: " + str(active_count()))
                print("Broken Watchdog, killing loop uuid: " + str(uuid))
                # Remove from userUUIDAssociations
                del userUUIDAssociations[uuid]
                break

async def updatePTZReadOut(rtcPeer, cameraName, channel_object):
    # Get Camera Info

    # THE CURRENT ISSUE I am having is with the event loops, because this get's called to run in another thread, but it still needs
    # to be awaitable, 
    # Current Warning Is: /usr/lib/python3.10/threading.py:953: RuntimeWarning: coroutine 'updatePTZReadOut' was never awaited
    # Ref Article: https://xinhuang.github.io/posts/2017-07-31-common-mistakes-using-python3-asyncio.html
    # https://lucumr.pocoo.org/2016/10/30/i-dont-understand-asyncio/

    # This was FIXED thanks to GPT-4, but through a special frontend phind.com, (https://www.phind.com/search?cache=fc03e656-53f9-4b1e-bfe4-8c4632d7fe5c)

    
    # Getting Current COORDS from camera
    myCursor.execute("Select * from localcameras where name = '{0}' ".format(cameraName))
    camtuple = myCursor.fetchall()
    camdata = camtuple[0]
    
    # While Object exists, send Coords
    # Since messages are random, we send a identifier + data sepeerated by |, so 'ptzcoordupdate|X Y'
    
    while True:
        ptzcoords = readPTZCoords(camdata[1], camdata[3], cryptocode.decrypt(str(camdata[4]), passwordRandomKey))
        # print("Updating Coords to {0}".format(ptzcoords))
        
        # Publish Here
        try:
            channel_object.send('ptzcoordupdate|' +str(ptzcoords))
        except:
            # Assume channel closed, return.
            return
        await asyncio.sleep(0.5)

def sendAuthenticatedPTZContMov(cameraName, direction, speed, tmpCamTuple):
    # Get camera credentials once
    
    if (tmpCamTuple == False):
        myCursor.execute("Select * from localcameras where name = '{0}' ".format(cameraName))
        camtuple = myCursor.fetchall()
        tmpCamTuple = True
    elif (tmpCamTuple == True):
        return
    
    # print(tmpCamTuple)

    
    camdata = camtuple[0]
    finalXVelocity = 0
    finalYVelocity = 0
    zoom = 0
    speed = (float(speed) * 0.10)

    if (direction == "up"):
        finalYVelocity = (speed)
    elif (direction == "down"):
        finalYVelocity = -(speed)
    elif (direction == "left"):
        finalXVelocity = -(speed)
    elif (direction == "right"):
        finalXVelocity = (speed)
    elif (direction == "positive"):
        zoom = 0.2
    elif (direction == "negative"):
        zoom = -0.2
    elif (direction == "stop"):
        finalXVelocity = 0
        finalYVelocity = 0
        zoom = 0
        tmpCamTuple = False

    
    sendContMovCommand(camdata[1], camdata[3], cryptocode.decrypt(str(camdata[4]), passwordRandomKey), finalXVelocity, finalYVelocity, zoom)

# Initializes objects and connections we need.
async def webRtcStart(thisUUID, dockerIP, cameraName):
    try:
        # Pingtime holds the UUID and the current ping time (Time since last ping pong message from client, if over 5 seconds or so get rid of)
        global userUUIDAssociations
            
        # Set Media Source and decode offered data
        # Media source being local docker container and regular video frames
        
        player = MediaPlayer("rtsp://" + dockerIP + ":8554/cam1")
        params = ast.literal_eval((request.data).decode("UTF-8"))


        # Set ICE Server to local server, hardcoded to be NVR, change at install!
        offer = RTCSessionDescription(sdp=params.get("sdp"), type=params.get("type"))
        webRtcPeer = RTCPeerConnection(configuration=RTCConfiguration(
        iceServers=[RTCIceServer(
            urls=['stun:nvr.internal.my.domain'])]))

        # We need to see if the camera supports PTZ, if it does prepare to send COORDS
        # Select all info about current cam
        myCursor.execute("Select * from localcameras where name = '{0}' ".format(cameraName))
        camtuple = myCursor.fetchall()
        camdata = camtuple[0]
        
        # Currently passing through the raw DB query.
        cameraModel = camdata[7]
        ptzcoords = {}
        myCursor.execute("Select hasptz, hastwa from cameradb where model = '{0}' ".format(cameraModel))
        hasEXTTuple = myCursor.fetchall()
        
        hasPTZ = hasEXTTuple[0][0]
        hasTWA = hasEXTTuple[0][1]    

        # Create Event Watcher On Data Channel To Know If Client Is Still Alive, AKA Ping - Pong
        @webRtcPeer.on("datachannel")
        def on_datachannel(channel):
            if (hasPTZ == True):
                ptzcoords = 'Supported' #PTZ Coords will be part of WebRTC Communication, send every 0.5 seconds.
                update_task = asyncio.create_task(updatePTZReadOut(webRtcPeer, cameraName, channel))  

            if (hasTWA == True):
                channel.send("truetwa") # Allows Remote TWA Toggle to be clicked

            tmpCamTuple = False

            @channel.on("message")
            async def on_message(message):
                global userUUIDAssociations
                if isinstance(message, str) and message.startswith("ping"):
                    userUUIDAssociations[thisUUID][1] = time.time()
                    channel.send("pong" + message[4:])
                elif (message.startswith("up:")):
                    msgSpeed = message.split(":")[1] 
                    sendAuthenticatedPTZContMov(cameraName, "up", msgSpeed, tmpCamTuple)

                elif (message.startswith("down:")):
                    msgSpeed = message.split(":")[1] 
                    sendAuthenticatedPTZContMov(cameraName, "down", msgSpeed, tmpCamTuple)

                elif message.startswith("left:"):
                    msgSpeed = message.split(":")[1] 
                    sendAuthenticatedPTZContMov(cameraName, "left", msgSpeed, tmpCamTuple)

                elif (message.startswith("right:")):
                    msgSpeed = message.split(":")[1]
                    sendAuthenticatedPTZContMov(cameraName, "right", msgSpeed, tmpCamTuple)

                elif (message.startswith("positive:")):
                    msgSpeed = message.split(":")[1]
                    sendAuthenticatedPTZContMov(cameraName, "positive", msgSpeed, tmpCamTuple)

                elif (message.startswith("negative:")):
                    msgSpeed = message.split(":")[1]
                    sendAuthenticatedPTZContMov(cameraName, "negative", msgSpeed, tmpCamTuple)

                elif (message == "stop"):
                    sendAuthenticatedPTZContMov(cameraName, "stop", 0, tmpCamTuple)
                    
                elif (message == "truetwa"):                
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
                    
                    # Now send to remote via threading.
                    microphoneStreamFuture = asyncio.create_task(
                    streamBufferToRemote(camdata[3], cryptocode.decrypt(str(camdata[4]), passwordRandomKey), cameraIP3[0], int(port3), slashAddress, webRtcPeer)
                    )
                    # Add instance to uuid
                    userUUIDAssociations[thisUUID].append(microphoneStreamFuture) # Appended to 5
                    
                elif (message == "falsetwa"):
                    # print("Cancel Microphone Task")
                    userUUIDAssociations[thisUUID][5].cancel()
                    await asyncio.sleep(0)
                    del userUUIDAssociations[thisUUID][5]
                    
                elif (message == "requestCameraControl"):
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
                            channel.send("controlallow")
                            # Set all to know I'm controlling
                            userUUIDAssociations[thisUUID][3] = True
                        elif (anyCamUsing == True):
                            # Is being used, control deny
                            channel.send("controldeny")
                    
                elif ():
                    # print("Closing Peer!")
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
    except asyncio.CancelledError:
        update_task.cancel()
        
# When we grab a WebRTC offer from out browser client.
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
    asyncio.set_event_loop(rtcloop)
        
    # Not sure if I'd be able to replace this, but should be fine as is.
    parsedSDP = rtcloop.run_until_complete(webRtcStart(thisUUID, dockerIPString, cam))
    
    # Now create a timer that is reset by Ping-Pong.

    # Add generated info to userUUIDAssociation
    # UUID, user[0], pingtime[1], rtcloopObject[2], userInTrackControl[3], camName[4], microphoneStreamFuture[5] (5 appended)
    userUUIDAssociations[thisUUID] = [thisUser, 0, rtcloop, False, cam]

    
    # Continue running that loop forever to keep AioRTC Objects In Memory Executing, while shifting it to
    # Another thread so we don't block the code.
    webRTCThread = Thread(target=rtcloop.run_forever)
    webRTCThread.start()
  
    # print("Current Number Of Running Threads: " + str(active_count()))
    
    # Return Our Parsed SDP to the client
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


def updateSnapshots():

    while True:
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
        print("Running Threads: " + str(active_count())) # We currently don't ever stop the started threads as
        time.sleep(8) # Time to wait between gathering snapshots
        # # Task Check
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # tasks = asyncio.all_tasks(loop)
        # for task in tasks:
        #     print("Print Task: " + str(task))

def startWebClient():
    # Testing Web Server
    # app.run(host='0.0.0.0')

    # Production web server
    print("Web Client Started.")
    serve(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    
    setCommitID()
    
    dockerComposer.firstRunDockerCheck = False

    # Start Docker Management Thread, which checks the localcameras table and using that determines if all docker containers are runnning.
    dockerThread = Thread(target=dockerWatcher)
    dockerThread.start()
    
    # Start rest of program after docker containers start
    
    while (dockerComposer.firstRunDockerCheck == False):
        # print("Docker check failed, waiting 5 seconds to check again.")
        time.sleep(5)

    if (dockerComposer.firstRunDockerCheck == True):
        print("Docker check True! Start Web Interface in 10 seconds")
          # Start Snapshot Thread.
        snapshotThread = Thread(target=updateSnapshots)
        snapshotThread.start()
        
        # UUID Pingtime watchdog thread, if any ping is above set threashold, grab rtcloop object and stop
        uuidWatchdog = Thread(target=uuidWatchdog) # Create a watchdog that takes the UUID and Event Loop
        uuidWatchdog.start()
        
        # Wait 10 seconds
        time.sleep(10)
        startWebClient()