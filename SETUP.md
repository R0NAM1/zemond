So you actually wanna use this program, eh?
To do that solve these riddle three:

HOW TO SETUP THE ZEMOND SECURITY PROGRAM
===R0NAM1 2024===

You can either setup Zemond on a Bare Metal host or a virtual machine, it's not picky.
Recommended to use Debian, GUI optional.

1. Create a Directory on Root with the name zemond (/zemond) that has normal user permissions, this will be where the Zemond program lives with Docker and Python.

2. Download the latest release and unpack the contents into the said directory, or git clone latest version of commit.

3. Make sure you have Docker and docker-compose installed along with python, install dependancies either system-wide, or with a Virutal Enviroment, which is preferred. (Run 'mkdir python/venv && python3 -m venv python/venv')
Then run 'source python/venv/bin/activate' to enter the venv, and to install the dependancies run 'pip3 install -r requirements.txt'

4. Make sure you have a storage directory configured, this can be the local files system, or any remote directory, make sure it is under (/zemond-storage)

5. We need to make a static network in docker now to host all the containers, we use a /16, which limits us to ~65,536 cameras. Each container will have a static address. Run the following:

'docker network create --subnet=172.25.0.0/16 zemond-nat'

Beacause docker containers run under nat, unless explicitly stated to forward ports. This means only the Zemond Host can communicate with these containers.

6. Go ahead and spin up the database by editing docker-compose.yml and changing POSTGRES_PASSWORD to something unique, then running the command 'docker-compose up -d postgres-zemond'. This should bring it up on the address 172.25.0.2. In globalFunctions.py, change the DB details to reflect your enviroment, or run Postgres another way, preferably on the same system.

7. We now need to build the base Docker Container that will host the camera, this can be done by running 'docker build . --tag zemond/cameramain:v1.0'

8. We also need to use a STUN server for client connectivity, APT has a coturn package you can use, whichever way you decide to implement a STUN server or a TURN server, you need to set it in two places: python/webrtc.py and python/static/js/stunServer.js
In both search for the string 'nvr.internal.my.domain' and set it to your specific STUN server.

9. Replace app.secret_key = 'IShouldBeUnique!' to a randomly generated string, use openssl as such:
'openssl rand -hex 40', using 40 characters to be more unique

Remember, YOU are responsible for the Operating System Security, Network Security and ALL attack vectors. Dosen't matter how well a program is made if you don't secure any path to it.
Security is layered.


# TODO

Figure out systemd process, make install script for that.

To test the server, run 'python3 app.py'

(In case requirements.txt changes, run pip3 freeze > requirements.txt)

Make Admin user for permission editing, users cannot edit their own perms, so make a specific super account
for that specific user. Seperate permissions. Ideally user-perm accounts only can access manage_perms, every
other account cant.

FOR USE IN FIREFOX, go to about:config and set the following:
- media.navigator.mediadatadecoder_vp8_hardware_enabled = true
- media.peerconnection.video.vp9_preferred = true
- media.webrtc.hw.h264.enabled = false
