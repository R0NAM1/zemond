# Simple file to subscribe to ONVIF Motion Events And Display Info About Events

import math
import threading
import requests
import os
import sys
import time
from requests.auth import HTTPDigestAuth
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from time import sleep

camera_username = 'admin'
camera_password = 'admin'


# SOAP request URL
url = "http://ip.address/onvif/device_service"

# Control an IP Camera's PTZ from an Xbox Controller!

# structured XML for GetStatus,
# Constantly Get Camera's PTZ Position.
payload = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver20/ptz/wsdl">
   <soap:Header/>
   <soap:Body>
      <wsdl:GetStatus>
         <wsdl:ProfileToken>MediaProfile00000</wsdl:ProfileToken>
      </wsdl:GetStatus>
   </soap:Body>
</soap:Envelope>"""
# headers
headers = {
    'Content-Type': 'text/xml; charset=utf-8'
}

# class XboxController(object):
#     MAX_TRIG_VAL = math.pow(2, 8)
#     MAX_JOY_VAL = math.pow(2, 15)

# print(XboxController.
while True:
    # POST request
    response = requests.request("POST", url, headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
    
    # prints the response
    # print(response.text)
    # print(response)

    parsedResponseXML = BeautifulSoup(response.text, 'xml')
    panTiltPosition = parsedResponseXML.find("tt:PanTilt")
    sys.stdout.write("Current X: " + panTiltPosition.get("x") + " ---- " + "Current Y: " + panTiltPosition.get("y") + "\r")
    sys.stdout.flush()
    sleep(0.05)
