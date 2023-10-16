# This file handles Onvif PTZ for a camera by allowing it to be published with
# Camera, Co-ords, Speed.
# Or Read By Calling ReadPTZCoords
import cryptocode, asyncio
from onvifRequests import *
from globalFunctions import passwordRandomKey, sendONVIFRequest, myCursor, myDatabase
from bs4 import BeautifulSoup

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

def readPTZCoords(onvifURL, username, password):
    # print("Getting PTZ Coords")
    response = sendONVIFRequest(GetCurrentPTZ, onvifURL, username, password)
    parsedResponseXML = BeautifulSoup(response.text, 'xml')
    panTiltPosition = parsedResponseXML.find("tt:PanTilt")
    assembledPTZCoords = {"X": panTiltPosition.get("x"), "Y": panTiltPosition.get("y")}
    return assembledPTZCoords

def sendContMovCommand(onvifURL, username, password, xvelocity, yvelocity, zoompos):
    modConPTZMov1 = continiousPtzMove.replace("{RP1}", str(xvelocity))
    modConPTZMov2 = modConPTZMov1.replace("{RP2}", str(yvelocity))
    modConPTZMov3 = modConPTZMov2.replace("{RP3}", str(zoompos))
    response = sendONVIFRequest(modConPTZMov3, onvifURL, username, password)
    return (response.text)

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