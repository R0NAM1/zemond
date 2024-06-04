import psycopg2 
import requests
from requests.auth import HTTPDigestAuth

global userUUIDAssociations, sigint

def sendONVIFRequest(payload, onvifURL, username, password):
    headers = {
        'Content-Type': 'text/xml; charset=utf-8'
        }
        # POST request
    return requests.request("POST", onvifURL, headers=headers, data=payload, auth=HTTPDigestAuth(username, password))

passwordRandomKey = 'ChangeMeTooooooo!'

userUUIDAssociations = {}

sigint = False

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

# Dashboard variables
# Threads
threadsRunning = 0
threadsArray = []

# CPU
systemCpu = 0

# MEMORY
systemMem = 0

# Users viewing cameras arrays
sessionsArray = []