import json

# This is the docker composer! This is the file that handles all the logic for manipulating docker-compose.yml 
# and starting or stopping docker containers!

from globalFunctions import myCursor, myDatabase, passwordRandomKey
import docker, os, time, cryptocode

global firstRunDockerCheck
firstRunDockerCheck = False;

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

    runningContainers = [container.name for container in (dockerClient.containers.list(all=True))]

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

def dockerWatcher():

    # On First Run, Check If The Docker Daemon is Running, if not warn user!
    # We can check if the docker systemd process is running by checking if '/var/run/docker.pid' exists.
    # If it does then it will output the PiD of the dockerd daemon.

    if os.path.isfile('/var/run/docker.pid'):
        print("Seems like dockerd is running....")
    else:
        print("Couldn't find a PiD File For Docker! Is it running...?")

    while True:
        print("Checking If All Proper Containers Are Running...")

        # Go through each entry in the DB and make sure the corosponding container is running
        myCursor.execute("Select name, dockerIP from localcameras")
        camdump = myCursor.fetchall()
        camnames = []
        camips = []
        
        for name, ip in camdump:
            camnames.append(name)
            camips.append(ip)

        cameraDBIP = ''

        for camera in camnames:
            cameraNameHash = camera.replace(" ", "-")
            # print("Checking container associated with " + cameraNameHash)

            # Get Database IP associated
                
            for name, ip in camdump:
                if name == camera:
                    cameraDBIP = ip
            
            # Get list of all existing docker containers:
            containers = [container.name for container in (dockerClient.containers.list(all=True))]

            # print(containers)

            # camera[0] needs to have 'spaces' replaced with '-' for docker container names


            # Check If Containers Exist
            if cameraNameHash in containers:
                
                # print("Docker Container Exists! Checking if its running...")
                iContainer = dockerClient.containers.get(cameraNameHash)
                container_state = iContainer.attrs['State']

                if container_state['Status'] == 'running':
                    print(cameraNameHash + " is Running! Checking if IP Matches database record...")
                    # Now check if IP matches
                    if ((iContainer.attrs['NetworkSettings']["Networks"]["zemond-nat"]['IPAddress']) == cameraDBIP):
                        print("Camera DB and IP Match, nothing to do! \n \n")
                    else:
                        containerIP = (iContainer.attrs['NetworkSettings']["Networks"]["zemond-nat"]['IPAddress'])
                        print("Did Not Match: DBIP:" + cameraDBIP + ": UPDATE dockerIP ON DATABASE TO: " + str(containerIP))
                        myCursor.execute("UPDATE localcameras SET dockerIP='{0}' WHERE name = '{1}'".format(containerIP, camera))
                        myDatabase.commit()
                else:
                    iContainer.start()
                    # Wait 5 seconds for container to start
                    time.sleep(5)

                    iContainer.reload()
                    # We also need to update the IP here
                    containerIP = (iContainer.attrs['NetworkSettings']["Networks"]["zemond-nat"]['IPAddress'])

                    print("Starting Docker Container: " + cameraNameHash + " :updating database record IP to " + containerIP) 
                    
                    myCursor.execute("UPDATE localcameras SET dockerIP='{0}' WHERE name = '{1}'".format(containerIP, camera))
                    myDatabase.commit()

            else:
                myCursor.execute("Select rtspurl from localcameras where name='{0}'".format(camera))
                currentiurl = myCursor.fetchone()
                currentiurlString = ''.join(currentiurl)
                # Get Current Camera's Username
                myCursor.execute("Select username from localcameras where name='{0}'".format(camera))
                currentiusername = myCursor.fetchone()
                currentiusernameString = ''.join(currentiusername)
                # Get Current Camera's Password
                myCursor.execute("Select password from localcameras where name='{0}'".format(camera))
                currentipassword = myCursor.fetchone()
                currentipasswordString = ''.join(currentipassword)
                myCursor.execute("Select rtspurl from localcameras where name='{0}'".format(camera))
                rtspurl =  myCursor.fetchone()
                rtspurl =  ''.join(rtspurl)
                rtspurl2 = rtspurl.replace("rtsp://", "")
                ip, port = rtspurl2.split(":", 1)
                port = port.split("/", 1)[0]
                address, params = rtspurl.split("/cam", 1)
                rtspCredString = currentiurlString[:7] + currentiusernameString + ":" + cryptocode.decrypt(str(currentipasswordString), passwordRandomKey) + "@" + currentiurlString[7:]
                            
                            
                # Create Container if it does not exist
                # addRunningContainer(camera, rtspCredString, "268435456", "48")
                
        # For first run, set var to show containers have been checked.
        global firstRunDockerCheck
        firstRunDockerCheck = True
        # print("SETTING firstRunDockerCheck TO TRUE: " + str(firstRunDockerCheck))

        # Wait 5 seconds to re-check if containers exist
        time.sleep(5)



def removeContainerCompletely(cameraName):
    print("Prompted to remove container: " + cameraName)
    
    # First stop the container, then remove it.
    cameraNameHash = cameraName.replace(" ", "-")
    localContainer = dockerClient.containers.get(cameraNameHash)
    localContainer.stop()
    time.sleep(5)
    localContainer.remove()
