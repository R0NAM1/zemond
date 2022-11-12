import json

# This is the docker composer! This is the file that handles all the logic for manipulating docker-compose.yml 
# and starting or stopping docker containers!

from globalFunctions import myCursor, myDatabase
import docker

dockerClient = docker.from_env()

def addRunningContainer(cameraName, rtspCredentialString, clipSize, clipLimit):
    cameraNameHash = cameraName.replace(" ", "-")
    print("Adding a docker container for camera {0} if it does not exist.".format(cameraNameHash))

    # First we need to check if the container already exists, if it does and it's running refuse to create a new one.

    # If it does not exist, create a container based on the following command:
    # docker run --name (cameraNameHash) --env 'TZ=America/Los_Angles' --env 'RTSP_PATHS_CAM1_SOURCE=(rtspCredentialString)'

    # --env 'RTSP_PROTOCOLS=tcp' --env 'CLIP_SIZE=(CHOSEN)' --env 'CLIP_LIMIT=(CHOSEN)' --env 'CAMERA_NAME=(cameraNameHash)'

    # --env 'CAMERA_NAME_SPACE=(cameraName)' --volume /zemond/:/zemond --volume /mnt/NAS/Zemond-Storage/:/zemond-storage

    # --volume ./zemond-temp:/zemond-temp --restart unless-stopped

    # zemond/cameramain:v1.0 

    runningContainers = [container.name for container in (dockerClient.containers.list())]

    print(runningContainers)

    # Container does not exist and is not running, create it!

    if (cameraNameHash in runningContainers):
        print("Container Exists and is running, Don't Create!")
    else:

        # Add Enviroment Variables Here

        enviromentVars = {"TZ": "America/Los_Angles", "RTSP_PATHS_CAM1_SOURCE": rtspCredentialString, "RTSP_PROTOCOLS": "udp",
        "CLIP_SIZE": clipSize, "CLIP_LIMIT": clipLimit, "CAMERA_NAME": cameraNameHash, "CAMERA_NAME_SPACE": cameraName}

        # Add Volumes mounted here, setup for a local cache right now and offload to NAS when complete.

        volumeMappings = {"/zemond/": {"bind": "/zemond", "mode": "rw"}, 
        "/mnt/NAS/Zemond-Storage/": {"bind": "/zemond-storage", "mode": "rw"}, 
        "/zemond-temp": {"bind": "/zemond-temp", "mode": "rw"}}

        print(dockerClient.containers.run(network="zemond-nat", detach=True, image="zemond/cameramain:v1.0" ,name=cameraNameHash, environment=enviromentVars, volumes=volumeMappings, restart_policy={"Name": "unless-stopped"}))

        print([container.name for container in (dockerClient.containers.list())])

        # Now that the container exists, get it's IP address and log it to the DB

        localContainer = dockerClient.containers.get(cameraNameHash)

        containerIP = (localContainer.attrs['NetworkSettings']["Networks"]["zemond-nat"]['IPAddress'])

        myCursor.execute("UPDATE localcameras SET dockerIP='{0}' WHERE name = '{1}'".format(containerIP, cameraName))
        myDatabase.commit()