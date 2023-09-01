<img src="python/static/pictures/logo.png" alt="Zemond Logo" width="200"/> <br />
Zemond is a simple, lightweight and hackable NVR solution that is bash script and python for the utmost configurability.

Programs Used:
- RTSP-SIMPLE-SERVER for rebroadcasting the camera's RTSP stream to save bandwidth in LAN. (https://github.com/aler9/rtsp-simple-server)
- Docker, for process seperation.
- SupervisorD, for process management.
- FFMPEG, For Recording to Disk.
- Python and Flask for the Webserver.

Zemond runs with a Flask server, and Docker Containers for the active running code. The python takes care of the Webserver and other tasks needed, while Docker isolates the individual camera processes, in each Container runs the following processes:

- Supervisord, which is the inital spawned process.
- camera_ffmpeg.sh, which is the looping script that records RTSP to Disk.
- camera_watchdog.sh, Which watches the resulting video file and when a size condition is met, kills all ffmpeg processes in the container.
- rtsp-server, which rebroadcast's the Camera's RTSP stream.
- onvif-watchdog, which logs ONVIF events to the database, (Shares globalfunctions.py with DB Object) (Includes Motion Events)

This is by default, any and all of this is configurable.

Eventually will also support SIP to two way audio cameras, since SIP phones are often more convenient then headsets.