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
- User audit log (Done)
- Voice from a SIP endpoint to the zemond server, routed to the camera. (Later)
- User management. (About done, do ldap later)
- Multi-monitor mode, with maps you can customize and preset dashboards.
- A timeline search, so you can export and snapshot certain chunks of footage.
- Plugins for (AI detection, license plate detection, other behaviors), just ran as a seperate thread definition.
- Custom video element controls
- Docker swarm integration so we can have multiple nodes for distributed processing
- Kill user cookies after an hour or configurable unless designated as monitor
- Premade groups for use immediently

(Snapshots and promo crap, reference other git repos)

# To Do:
- ✓ Change M3u8FileWriter to use 1 minute segments and stop after remaining time in minute, forces it to stay locked to a minute
- ✓ Fix AioRTC left over tasks
- Have encoding options available through HTTP and modified with env vars in the m3u8 script.
- Add Used Threads, Ram CPU and Amount of Clients On Dashboard
- Fix Timeline head positioning to keep both videos in sync, change based on length and use that timestamp to set all videos,
- Main Camera View Change Style
- Finish timeline viewer with exporter
- Add Timeline Player ghost controls, go away after 2 seconds or mouse off
- Figure out variable time marker for player according to percentage or something?
- Add 32x and 64x for timeline viewer
- Have AioRTC cameraViewers stop if no clients for one minute or so
- Add time check to WebRTC code to reload page if midnight, to prevent Server Side Qlong integer overflow
- Make database calls own file with try and catchs
- Alarm & silent alarm mode that sends notifications, and/or activates sirens and can send network request or serial data to physcial security system box
- Ai detection plugin that uses npu(s) and custom user uploadable models

(May have to use)
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' blob: data:; img-src 'self' data:; style-src 'self' 'unsafe-inline'; media-src 'self' blob: data:;">