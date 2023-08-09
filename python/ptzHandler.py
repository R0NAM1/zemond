# This file handles Onvif PTZ for a camera by allowing it to be published with
# Camera, Co-ords, Speed.
# Or Read By Calling ReadPTZCoords
from onvifRequests import *
from globalFunctions import passwordRandomKey, sendONVIFRequest
from bs4 import BeautifulSoup


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