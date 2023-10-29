import av, asyncio, fractions, time
import logging as logger
from aiortc.mediastreams import MediaStreamTrack
from aiortc.contrib.media import REAL_TIME_FORMATS
from av import VideoFrame, AudioFrame
from threading import Thread, Event

cameraPlayerDictionary = {}

# Set AV logging, useful for if a stream is erroring for some reason, usually redundant
# av.logging.set_level(av.logging.PANIC)

class CameraPlayerTrack(MediaStreamTrack):
    # This track is made in webRtc.py and accepts the CameraPlayer object to read buffer from
    def __init__(self, cameraplayer, kind, uuid):
        super().__init__() # Init Class
        self.cameraplayer = cameraplayer # CameraPlayer reference
        self.kind = kind # Video or audio?
        self.lb = None # Last recv frame
        self._id = 'cameraplayertrack.' + str(kind) + '.' + str(uuid) # Semi Custom ID
                
    # Consumer wants frame, get latest from CameraPlayer, or return blank.
    async def recv(self):
        # Don't async wait for latest frame, instead if I have a frameBuffer and it is not the last frame I processed, or return last frame
        if self.kind == 'video':
            if (self.cameraplayer.videoFrameBuffer is not None) and (self.cameraplayer.videoFrameBuffer is not self.lb):
                self.lb = self.cameraplayer.videoFrameBuffer
                return self.cameraplayer.videoFrameBuffer
            elif self.cameraplayer.videoFrameBuffer is None:
                # print("Sending Blank Video Frame")
                frame = VideoFrame(width=1280, height=720)
                frame.pts = 0
                frame.time_base = '1/90000'
                return frame
            else:
                # print("Resend Video")
                return self.lb
            
        # If I want audio
        elif self.kind == 'audio':
            if (self.cameraplayer.audioFrameBuffer is not None) and (self.cameraplayer.audioFrameBuffer is not self.lb):
                self.lb = self.cameraplayer.audioFrameBuffer
                return self.cameraplayer.audioFrameBuffer
            elif self.cameraplayer.audioFrameBuffer is None:
                # print("Sending Blank Audio Frame")
                frame = AudioFrame(samples=960)
                frame.pts = 0
                frame.rate = 48000
                return frame
            else:
                # print("Resend Audio")
                return self.lb
                      
# Modified Media Player
class CameraPlayer():
    def __init__(self, dockerIp, decode=True):
        self.__container = av.open(file="rtsp://" + dockerIp + ":8554/cam1", mode="r", options={'hwaccel': 'auto'}) # Open Cam Stream
        self.__thread: Optional[threading.Thread] = None # Thread to get frames
        self.__thread_quit: Optional[threading.Event] = None # Thread end event

        # Examine streams
        self.__streams = [] # Streams in container, audio and video
        self.__decode = decode # Always decode
        self.audioFrameBuffer: Optional[AudioFrame] = None # Init public buffer to one type
        self.videoFrameBuffer: Optional[VideoFrame] = None
        self._parasites = 0
        
        # For loop that opens each data stream in av.container
        for stream in self.__container.streams:
            # Handle Audio
            if stream.type == "audio" and not self.audioFrameBuffer:
                if self.__decode:
                    self.__streams.append(stream)
                elif stream.codec_context.name in ["opus", "pcm_alaw", "pcm_mulaw"]:
                    self.__streams.append(stream)
            # Handle Video
            elif stream.type == "video" and not self.audioFrameBuffer:
                if self.__decode:
                    self.__streams.append(stream)
                elif stream.codec_context.name in ["h264", "vp8"]:
                    self.__streams.append(stream)

        # check whether we need to throttle playback
        container_format = set(self.__container.format.name.split(","))
        self._throttle_playback = not container_format.intersection(REAL_TIME_FORMATS)

        # Still object creation, auto start worker thread
        self._start()

    def _start(self):
        # Create thread if None
        if self.__thread is None:
            self.__thread_quit = Event()
            self.__thread = Thread(
                name="camera-player",
                target=player_worker_decode,
                args=(
                    asyncio.get_event_loop(),
                    self.__container,
                    self.__streams,
                    self,
                    self.__thread_quit,
                    self._throttle_playback,
                ),
            )
            self.__thread.start()

    # Implement when I make cameraPlayer watchdog so cameraPlayers can only exist when a cameraPlayer has at least one track attatched?
    # Monitor through CameraPlayer._parasites as int? If is 0 then run cameraPlayer._stop
    # def _stop(self, track: PlayerStreamTrack) -> None:
    #     self.__started.discard(track)

    #     if not self.__started and self.__thread is not None:
    #         self.__log_debug("Stopping worker thread")
    #         self.__thread_quit.set()
    #         self.__thread.join()
    #         self.__thread = None

    #     if not self.__started and self.__container is not None:
    #         self.__container.close()
    #         self.__container = None

# Decoder
def player_worker_decode(loop, container, streams, cameraplayer, quit_event, throttle_playback):
    # Set audio dials
    audio_samples = 0
    # Keeping sample bit length and sample rate, just changing formats
    audio_resampler = av.AudioResampler(
        format="s16"
    )

    #Init frame
    video_first_pts = None

    frame_time = None
    start_time = time.time()
    

    # While my quit event isn't set
    while not quit_event.is_set(): 
        try:
            # Get next frame from the container streams
            frame = next(container.decode(*streams))
        except Exception as exc:
            if isinstance(exc, av.FFmpegError) and exc.errno == errno.EAGAIN:
                time.sleep(0.01)
                continue
            if isinstance(exc, StopIteration) and loop_playback:
                container.seek(0)
                continue
            if cameraplayer.audioFrameBuffer:
                cameraplayer.audioFrameBuffer = None
            if cameraplayer.videoFrameBuffer:
                cameraplayer.videoFrameBuffer = None
            break
        
        # read up to 1 second ahead
        if throttle_playback:
            elapsed_time = time.time() - start_time
            if frame_time and frame_time > elapsed_time + 1:
                time.sleep(0.1)
                
        # Handeling an audio frame
        if isinstance(frame, AudioFrame):
            # print("1: " + str(frame))
            for frame in audio_resampler.resample(frame):
                # fix timestamps
                frame.pts = audio_samples
                audio_samples += frame.samples

                frame_time = frame.time
                # Put into buffer
                # print("Write to buffer: " + str(frame))
                cameraplayer.audioFrameBuffer = frame
        elif isinstance(frame, VideoFrame):
            if frame.pts is None:  # pragma: no cover
                logger.warning(
                    "MediaPlayer(%s) Skipping video frame with no pts", container.name
                )
                continue

            # video from a webcam doesn't start at pts 0, cancel out offset
            if video_first_pts is None:
                video_first_pts = frame.pts
            frame.pts -= video_first_pts

            frame_time = frame.time
            # Put into buffer
            cameraplayer.videoFrameBuffer = frame
            