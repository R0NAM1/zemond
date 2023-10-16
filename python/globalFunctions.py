import psycopg2 
import requests
from requests.auth import HTTPDigestAuth

global userUUIDAssociations

def sendONVIFRequest(payload, onvifURL, username, password):
    headers = {
        'Content-Type': 'text/xml; charset=utf-8'
        }
        # POST request
    return requests.request("POST", onvifURL, headers=headers, data=payload, auth=HTTPDigestAuth(username, password))

passwordRandomKey = 'ChangeMeTooooooo!'

userUUIDAssociations = {}

databaseURL = '10.0.0.15'
databasePort = 5432
databaseUser = 'zemond'
databaseName = 'zemond'
databaseUserPassword = 'uniquePassword'

myDatabase = psycopg2.connect(database=databaseName,
                        host=databaseURL,
                        user=databaseUser,
                        password=databaseUserPassword,
                        port=databasePort)

myCursor = myDatabase.cursor()