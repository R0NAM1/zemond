from globalFunctions import sendONVIFRequest
from globalFunctions import myCursor
from globalFunctions import myDatabase
from globalFunctions import passwordRandomKey
from flask import session, flash
from bs4 import BeautifulSoup
from onvifRequests import *
from twoWayAudio import describePROBE
import cryptocode

import sys
# This file has the definition that takes a Camera Name, queries the DB for it to verify it's imported, then do all other autoconfig
# With ONVIF

def onvifAutoconfigure(cameraname):
    # First we have to finish out DB entries, get Model, Serial, Firmware Number and RTSP Stream URL

    myCursor.execute("Select onvifurl from localcameras Where name = '{0}'".format(cameraname))
    onvifURL = myCursor.fetchone()
    onvifURLString = ''.join(onvifURL)
    # String Format: [('http://x.x.x.x/onvif/device_service',)]

    # Now That we have the ONVIF URL, get credentials, then the above.
    myCursor.execute("Select username from localcameras Where name = '{0}'".format(cameraname))
    camerausername = myCursor.fetchone()
    camerausernameString = ''.join(camerausername)
    myCursor.execute("Select password from localcameras Where name = '{0}'".format(cameraname))
    cameraencryptedpassword = myCursor.fetchone()
    cameraencryptedpasswordString = ''.join(cameraencryptedpassword)

    # Get General Device Info

    response = sendONVIFRequest(GetDeviceInformation, onvifURLString, camerausernameString, cryptocode.decrypt(str(cameraencryptedpasswordString), passwordRandomKey))

    parsedResponseXML = BeautifulSoup(response.text, 'xml')

    cameraManufacturer = parsedResponseXML.find_all('tds:Manufacturer')[0].text
    cameraModel = parsedResponseXML.find_all('tds:Model')[0].text
    cameraFirmwareVersion = parsedResponseXML.find_all('tds:FirmwareVersion')[0].text
    cameraSerialNumber = parsedResponseXML.find_all('tds:SerialNumber')[0].text

    # Get Device Stream URI

    response = sendONVIFRequest(GetRTSPURL, onvifURLString, camerausernameString, cryptocode.decrypt(str(cameraencryptedpasswordString), passwordRandomKey))

    parsedResponseXML = BeautifulSoup(response.text, 'xml')

    cameraRTSPURL = parsedResponseXML.find_all('tt:Uri')[0].text

    # Now we have all the relevent Camera Info, upload to DB

    try:
        myCursor.execute("UPDATE localcameras SET rtspurl=%s, model=%s, serialnumber=%s, firmwareversion=%s, manufacturer=%s WHERE name = '{0}'".format(cameraname), (str(cameraRTSPURL), str(cameraModel), str(cameraSerialNumber), str(cameraFirmwareVersion), str(cameraManufacturer)))
    except Exception as e:
                                session.pop('_flashes', None)
                                flash('Database couldnt be written to, the following exception was raised: ' + str(e))
                                # Delete written info
                                myCursor.execute("DELETE FROM localcameras where name = '{0}'").format(cameraname)
                                myDatabase.commit()
                                raise e
    else:
        myDatabase.commit()

    # Now that we've added the camera to the local DB. we should store the general data in cameradb IF it does not exist, check
    # With Model

    myCursor.execute("Select model from cameradb Where model = '{0}'".format(str(cameraModel)))
    myCursor.fetchone()
    if  (myCursor.rowcount == 0):
        # Does camera have PTZ? Send Request GetCurrentPTZ, answer depends on response

        response = sendONVIFRequest(GetCurrentPTZ, onvifURLString, camerausernameString, cryptocode.decrypt(str(cameraencryptedpasswordString), passwordRandomKey))
        parsedResponseXML = BeautifulSoup(response.text, 'xml')

        hasPTZ = 'Zero';

        # try:
        hasPTZ = parsedResponseXML.find_all('s:Value')
        #[<s:Value>s:Receiver</s:Value>, <s:Value>ter:ActionNotSupported</s:Value>, <s:Value>ter:PTZNotSupported</s:Value>]
        
        if any("<s:Value>ter:PTZNotSupported</s:Value>" for s in hasPTZ):
            print("PTZ NOT SUPPORTED!")
            hasPTZ = False;
        else:
            hasPTZ = True;


        # Does camera have Two Way Audio? Can now figure out by calling twoWayAudio.py, describePROBE

        hasTWA = False;
        
        #Figure out IP PORT SLASHADDRESS from cameraRTSPURL
                
        ip1 = cameraRTSPURL.split("//")
        ip2 = ip1[1].split(":")
        ip3 = ip2[0]
        port1 = ip2[1].split("/")
        port2 = int(port1[0])
        slashAddress1 = ip2[1].split("554")
        slashAddress2 = slashAddress1[1]
        
        hasTWA = describePROBE(camerausernameString, cryptocode.decrypt(str(cameraencryptedpasswordString), passwordRandomKey), ip3, port2, slashAddress2, "zemond/1.0")

        print("Does support Two Way Audio?: " + hasTWA)

        myCursor.execute("INSERT INTO cameradb (model, manufacturer, hasptz, hastwa) VALUES(%s, %s, %s, %s)", (str(cameraModel), str(cameraManufacturer), hasPTZ, hasTWA))
        myDatabase.commit()
    else:
        print("Not Adding To cameradb, already exists", file=sys.stderr)


    
    
