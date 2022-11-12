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
   print("Unsubscribing from Subscriptions 0 - 20...")
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
   i = 0
   while i < 20:
      print(requests.request("POST", "http://ip.address/onvif/Subscription?Idx={0}".format(i), headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password)).text)
      i = i + 1
   
   time.sleep(5)

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

print("Parsing XML Response...")
print("")
print("")
print("")

parsedResponseXML = BeautifulSoup(response.text, 'xml')

try:
   subscriptionURL = parsedResponseXML.find_all('wsa5:Address')[0].text
except:
   print("Assigning Subscription URL gave an exemption, should send a 'Camera Restart'")
   
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
while True:
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
   
   print("Sending Request For Notification, Waiting For Response...")
   
   response = requests.request("POST", subscriptionURL, headers=headers, data=payload, auth=HTTPDigestAuth(camera_username, camera_password))
    
   # print(response.text)

   print("Got Response, Parsing And Dumping...")

   messagesXML =  BeautifulSoup(response.text, 'xml')

   # With XML Here, we need to break down the response into it's individual messages.

   messages = messagesXML.find_all('NotificationMessage')

   # Now we have each 'message' seperated, we can run a loop based on this:

   for message in messages:
         # Parse Each message to a string, following the format: Topic | Time | Data
          print("==========MESSAGE START===========")

          tmpXML = BeautifulSoup(str(message), 'xml')

         #  print("Raw: " + str(tmpXML))

          # Get Topic
          thisTopic = tmpXML.find('Topic')
          print("Topic: " + str(thisTopic.text))

          # Get Time
          thisTime = tmpXML.find('Message', {'UtcTime': True})
          thisTime = thisTime.get('UtcTime')
          print("Timestamp: " + str(thisTime))

          # Get Data
          thisData = tmpXML.find_all('SimpleItem')
          # Itterate Over Data
          i = 0
          for items in thisData:        
            thisObject = thisData[i].get('Name')
            thisValue = thisData[i].get('Value')
            print("Object: " + thisObject + " | Value: " + thisValue)
            i = i + 1      

          print("==========MESSAGE STOP============")
          print("")


