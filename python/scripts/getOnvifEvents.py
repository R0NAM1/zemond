# Simple file to subscribe to ONVIF Motion Events And Display Info About Events

import requests
import os
import time
from requests.auth import HTTPDigestAuth
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from time import sleep

camera_username = 'admin'
camera_password = 'admin'


# SOAP request URL
url = "http://ip.address/onvif/device_service"

initialTerminationTime = datetime.utcnow() + timedelta(hours=1)
initialTerminationTime = initialTerminationTime.strftime('%Y-%m-%dT%H:%M:%SZ')
print(initialTerminationTime)

# Cleanup, unsubscribe to 5 streams

def cleanup():
  print("Unsubscribing from Subscriptions 0 - 4...")
  payload = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:b="http://docs.oasis-open.org/wsn/b-2">
  <soap:Header/>
  <soap:Body>
  <b:Unsubscribe>
  <!--You may enter ANY elements at this point-->
  </b:Unsubscribe>
  </soap:Body>
  </soap:Envelope>"""
  # headers
  headers = {
    'Content-Type': 'text/xml; charset=utf-8'
    }
    # POST request
  requests.request("POST", "http://ip.address/onvif/Subscription?Idx=0", headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
  requests.request("POST", "http://ip.address/onvif/Subscription?Idx=1", headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
  requests.request("POST", "http://ip.address/onvif/Subscription?Idx=2", headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
  requests.request("POST", "http://ip.address/onvif/Subscription?Idx=3", headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
  requests.request("POST", "http://ip.address/onvif/Subscription?Idx=4", headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))

cleanup()

# structured XML for CreatePullPointSubscription,
# Step 1, create a Event Subscription On Remote Camera, InitialTerminationTime will be now + one hour.
payload = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver10/events/wsdl">
   <soap:Header/>
   <soap:Body>
      <wsdl:CreatePullPointSubscription>
         <!--Optional:-->
         <wsdl:Filter>
            <!--You may enter ANY elements at this point-->
         </wsdl:Filter>
         <!--Optional:-->
         <wsdl:InitialTerminationTime>""" + initialTerminationTime + """</wsdl:InitialTerminationTime>
         <!--Optional:-->
         <wsdl:SubscriptionPolicy>
            <!--You may enter ANY elements at this point-->
         </wsdl:SubscriptionPolicy>
         <!--You may enter ANY elements at this point-->
      </wsdl:CreatePullPointSubscription>
   </soap:Body>
</soap:Envelope>"""
# headers
headers = {
    'Content-Type': 'text/xml; charset=utf-8'
}
# POST request
response = requests.request("POST", url, headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
  
# prints the response
# print(response.text)
# print(response)

print("Parsing XML Response...")
print("")
print("")
print("")

parsedResponseXML = BeautifulSoup(response.text, 'xml')

subscriptionURL = parsedResponseXML.find_all('wsa5:Address')[0].text
subscriptionResponseTime = parsedResponseXML.find_all('wsnt:CurrentTime')[0].text
subscriptionTerminationTime = parsedResponseXML.find_all('wsnt:TerminationTime')[0].text

subscriptionTerminationTimeObject = datetime.strptime(subscriptionTerminationTime, '%Y-%m-%dT%H:%M:%SZ')

subscriptionTerminationTimeEpoch = (time.mktime(subscriptionTerminationTimeObject.timetuple())) # Time Subscription Ends In Unix EPOCH

currentTimeEpoch = (time.mktime(datetime.utcnow().timetuple()))

print("Subscription URL: " + subscriptionURL)
print("Subscription Response Time: " + subscriptionResponseTime)
print("Subscription Termination Time: " + subscriptionTerminationTime)

# Now we have the Subscription, we'll use the time as a loop condition to check when we should renew the subscription.
# Everytime we loop, we can pull the last 5 Messages, for instance. The Request URL will now be the Subscription URL

# We should pull these into a local DB, for both history and timestamping, 

# while currentTimeEpoch < subscriptionTerminationTimeEpoch:
while True:
    # os.system('clear')
    print ("Current Epoch Time: " + str(currentTimeEpoch))
    # structured XML for PullMessages,
    # Step 2, get all messages from Subscription, then wait for new messages, including motion events!
    payload = """<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" xmlns:wsdl="http://www.onvif.org/ver10/events/wsdl">
   <soap:Header/>
   <soap:Body>
      <wsdl:PullMessages>
         <wsdl:Timeout>0.1</wsdl:Timeout>
         <wsdl:MessageLimit>10</wsdl:MessageLimit>
         <!--You may enter ANY elements at this point-->
      </wsdl:PullMessages>
    </soap:Body>
    </soap:Envelope>"""
    # headers
    headers = {
    'Content-Type': 'text/xml; charset=utf-8'
    }
    # POST request
    # response = requests.request("POST", subscriptionURL, headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
    
    response = """<?xml version="1.0" encoding="utf-8" standalone="yes" ?><s:Envelope xmlns:sc="http://www.w3.org/2003/05/soap-encoding" xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:tt="http://www.onvif.org/ver10/schema" xmlns:wsnt="http://docs.oasis-open.org/wsn/b-2" xmlns:tev="http://www.onvif.org/ver10/events/wsdl" xmlns:wsa5="http://www.w3.org/2005/08/addressing" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wstop="http://docs.oasis-open.org/wsn/t-1" xmlns:tns1="http://www.onvif.org/ver10/topics"><s:Header/><s:Body><tev:PullMessagesResponse><tev:CurrentTime>2022-10-12T00:09:40Z</tev:CurrentTime><tev:TerminationTime>2022-10-12T16:07:44Z</tev:TerminationTime><wsnt:NotificationMessage><wsnt:Topic Dialect="http://www.onvif.org/ver10/tev/topicExpression/ConcreteSet">tns1:RuleEngine/CellMotionDetector/Motion</wsnt:Topic><wsnt:Message><tt:Message UtcTime="2022-10-12T00:09:40Z" PropertyOperation="Changed"><tt:Source><tt:SimpleItem Name="VideoSourceConfigurationToken" Value="00000"/><tt:SimpleItem Name="VideoAnalyticsConfigurationToken" Value="00000"/><tt:SimpleItem Name="Rule" Value="00000"/></tt:Source><tt:Data><tt:SimpleItem Name="IsMotion" Value="true"/></tt:Data></tt:Message></wsnt:Message></wsnt:NotificationMessage><wsnt:NotificationMessage><wsnt:Topic Dialect="http://www.onvif.org/ver10/tev/topicExpression/ConcreteSet">tns1:VideoSource/MotionAlarm</wsnt:Topic><wsnt:Message><tt:Message UtcTime="2022-10-12T00:09:40Z" PropertyOperation="Changed"><tt:Source><tt:SimpleItem Name="Source" Value="00000"/></tt:Source><tt:Data><tt:SimpleItem Name="State" Value="true"/></tt:Data></tt:Message></wsnt:Message></wsnt:NotificationMessage></tev:PullMessagesResponse></s:Body></s:Envelope>"""

    messagesXML =  BeautifulSoup(response, 'xml')

    messageType = parsedResponseXML.find_all('wsnt:Topic')

    messageTime = parsedResponseXML.find_all('tt:Message')

    isDetectingMotion = parsedResponseXML.find("tt:SimpleItem", {"Name": "IsMotion"})

    print(response)
   #  print("")
   #  print (messageType[0].text)

   #  if messageType == 'tns1:RuleEngine/CellMotionDetector/Motion':
        

   #      if isDetectingMotion.get("Value") == 'true':
   #          print("Motion Detected at " + messageTime.get("UtcTime"))
   #          print("")

    # print(response.text)
    currentTimeEpoch = (time.mktime(datetime.utcnow().timetuple()))
    sleep(3)


