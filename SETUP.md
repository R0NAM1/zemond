So you actually wanna use this program, eh?
To do that solve these riddle three:

HOW TO SETUP THE ZEMOND SECURITY PROGRAM
===R0NAM1 2022===

You can either setup Zemond on a Bare Metal host or a virtual machine, it's not picky.
Recommended to use Debian, GUI optional.

1. Create a Directory on Root that has normal user permissions, this will be where the Zemond program lives with Docker and Python.

2. Download the latest release and unpack the contents into the said directory.

3. Make sure you have Docker and docker-compose installed along with python, install dependancies either system-wide, or with a Virutal Enviroment, which is preferred. (Run 'mkdir python/venv && python3 -m venv python/venv')
Then run 'source python/venv/bin/activate' to enter the venv, and to install the dependancies run 'pip3 install -r requirements.txt'

4. Make sure you have a storage directory configured, this can be the local files system, or anything you want. You can even treat it like cache.

5. We need to make a static network in docker now to host all the containers, we use a /16, which limits us to ~65,536 cameras. Each container will have a static address. Run the following:

'docker network create --subnet=172.25.0.0/16 zemond-nat'

Beacause docker containers run under nat, unless explicitly stated to forward ports. This means only the Zemond Host can communicate with these containers.

6. Go ahead and spin up the database by editing docker-compose.yml and changing POSTGRES_PASSWORD to something unique, then running the command 'docker-compose up -d postgres-zemond'. This should bring it up on the address 172.25.0.2. In globalFunctions.py, change the DB details to reflect your enviroment.

7. We now need to build the base Docker Container that will host the camera, this can be done by running 'docker build . --tag zemond/cameramain:v1.0'

8. We also need to use a STUN server for client connectivity, APT has a coturn package you can use, whichever way you decide to implement a STUN server or a TURN server, you need to set it in two places: app.py and webrtc-client.js
In both search for the string 'nvr.internal.my.domain' and set it to your specific STUN server.


# TODO

To test the server, run 'python3 app.py'