<img src="python/static/pictures/logo.png" alt="Zemond Logo" width="200"/> <br />
Zemond is a simple, lightweight and hackable NVR solution that is bash script and python for the utmost configurability.

Programs Used:
- RTSP-SIMPLE-SERVER for rebroadcasting the camera's RTSP stream to save bandwidth in LAN. (https://github.com/aler9/rtsp-simple-server)
- Docker, for process seperation.
- SupervisorD, for process management.
- FFMPEG, For Recording to Disk and streaming Two Way Audio to the camera.
- Python and Flask for the Webserver.

Zemond runs with a Flask server, and Docker Containers for the active running code. The python takes care of the Webserver and other tasks needed, while Docker isolates the individual camera processes, in each Container runs the following processes:

- Supervisord, which is the inital spawned process.
- camera_ffmpeg.sh, which is the looping script that records RTSP to Disk.
- camera_watchdog.sh, Which watches the resulting video file and when a size condition is met, kills all ffmpeg processes in the container.
- rtsp-server, which rebroadcast's the Camera's RTSP stream.
- onvif-watchdog, which logs ONVIF events to the database, (Shares globalfunctions.py with DB Object) (Includes Motion Events)

This is by default, any and all of this is configurable.

Zemond is great for the home, buisness or any other place that needs security. The following features are planned:
- Live Video and Audio to the Browser (Done)
- PTZ To the camera (Done)
- Voice to the camera from client (Done)
- Voice from a SIP endpoint to the zemond server, routed to the camera.
- User management.
- Multi-monitor mode, with maps you can customize and preset dashboards.
- A timeline search, so you can export and snapshot certain chunks of footage.
- Plugins for (AI detection, license plate detection, other behaviors), just ran as a seperate thread definition.
- User audit log
- Custom video element controls

(Snapshots and promo crap, reference other git repos)