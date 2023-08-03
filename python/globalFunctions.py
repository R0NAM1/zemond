import psycopg2 
import requests
from requests.auth import HTTPDigestAuth

def sendONVIFRequest(payload, onvifURL, username, password):
    headers = {
        'Content-Type': 'text/xml; charset=utf-8'
        }
        # POST request
    return requests.request("POST", onvifURL, headers=headers, data=payload, auth=HTTPDigestAuth(username, password))

passwordRandomKey = 'ChangeMeTooooooo!'


databaseURL = '10.36.0.243'
databasePort = 5432
databaseUser = 'zemond'
databaseName = 'zemond'
databaseUserPassword = '1987glados'

myDatabase = psycopg2.connect(database=databaseName,
                        host=databaseURL,
                        user=databaseUser,
                        password=databaseUserPassword,
                        port=databasePort)

myCursor = myDatabase.cursor()