import av, asyncio, fractions, time
import logging as logger
from aiortc.mediastreams import MediaStreamTrack, AUDIO_PTIME
from aiortc.contrib.media import REAL_TIME_FORMATS
from av import VideoFrame, AudioFrame
from threading import Thread, Event

cameraPlayerDictionary = {}

# Set AV logging, useful for if a stream is erroring for some reason, usually redundant

class VideoCameraPlayerTrack(MediaStreamTrack):
    # This track is made in webRtc.py and accepts the CameraPlayer object to read buffer from
    def __init__(self, cameraplayer, uuid):
        super().__init__() # Init Class
        self.cameraplayer = cameraplayer # CameraPlayer reference
        self.kind = 'video' # Video or audio?
        self._id = 'cameraplayertrack.video.' + str(uuid) # Semi Custom ID
        
    # Consumer wants frame, get latest from CameraPlayer, or return blank.
    async def recv(self):
        while True:
            try:
                return self.cameraplayer.videoFrameBuffer
            except:
                pass
               
           
               
class AudioCameraPlayerTrack(MediaStreamTrack):
    # This track is made in webRtc.py and accepts the CameraPlayer object to read buffer from
    def __init__(self, cameraplayer, uuid):
        super().__init__() # Init Class
        self.cameraplayer = cameraplayer # CameraPlayer reference
        self.kind = 'audio' # Video or audio?
        self._id = 'cameraplayertrack.audio.' + str(uuid) # Semi Custom ID
        self._bufferIndex = self.cameraplayer.audioFrameBufferIndex
        self._firstRead = False
    # Consumer wants frame, get latest from CameraPlayer.
    async def recv(self):
        while True:
            try:
                # Wait so we don't overread the buffer
                if self._firstRead == False:
                    self._firstRead = True
                    time.sleep(0.2)
                # We read to fast, found waiting for this long keeps the reader and writers indexes pretty consistant, don't need to complicate this
                # further! We lose about 4 frames every wrap, but is worth it.
                time.sleep(0.021)
                # Check if need to reset to player index, and set curr index
                if (self.cameraplayer.audioFrameBufferEOL and self._bufferIndex != 0):
                    # If buffer rest and my index is not zero, set zero and return new frame
                    self._bufferIndex = 0
                    return self.cameraplayer.audioFrameBuffer[self._bufferIndex]
                elif (self._bufferIndex > self.cameraplayer.audioFrameBufferIndex):
                    # If overrunning buffer, go back two frames, can likely remove though
                    #If reading above index, rewind one
                    self._bufferIndex -= 5
                    return self.cameraplayer.audioFrameBuffer[self._bufferIndex]
                else:
                    # Get frame from buffer and increase index
                    frame = self.cameraplayer.audioFrameBuffer[self._bufferIndex]
                    self._bufferIndex += 1
                    return frame
            except Exception as e:
                # print("Audio track exception: " + str(e))
                pass
                      
# Modified Media Player
class CameraPlayer():
    def __init__(self, dockerIp, cameraName, decode=True, newWidth=(1280), newHeight=(720)):
        av.logging.set_level(av.logging.PANIC)
        self.__container = av.open(file="rtsp://" + dockerIp + ":8554/cam1", mode="r", options={'hwaccel': 'auto'}) # Open Cam Stream
        self.__thread: Optional[threading.Thread] = None # Thread to get frames
        self.__thread_quit: Optional[threading.Event] = None # Thread end event
        self.cameraName = cameraName
        vFrame = VideoFrame(width=1280, height=720)
        vFrame.pts = 0
        vFrame.time_base = '1/90000'
        aFrame = AudioFrame(samples=960)
        aFrame.pts = 0
        aFrame.rate = 48000
        # Examine streams
        self.__streams = [] # Streams in container, audio and video
        self.__decode = decode # Always decode
        self.audioFrameBuffer = [aFrame]*100 # Init public buffer to one type
        self.audioFrameBufferIndex = 0
        self.audioFrameBufferEOL = False
        self.videoFrameBuffer: Optional[VideoFrame] = vFrame
        self.newWidth = newWidth
        self.newHeight = newHeight
        
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
                name=("camera-player-" + self.cameraName),
                target=player_worker_decode,
                args=(
                    asyncio.get_event_loop(),
                    self.__container,
                    self.__streams,
                    self,
                    self.__thread_quit,
                    self._throttle_playback,
                    self.newWidth,
                    self.newHeight
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
def player_worker_decode(loop, container, streams, cameraplayer, quit_event, throttle_playback, newWidth, newHeight):
    # Set audio dials
    audio_samples = 0
    audio_sample_rate = 48000
    audio_time_base = fractions.Fraction(1, audio_sample_rate)
    # Keeping sample bit length and sample rate, just changing formats
    audio_resampler = av.AudioResampler(
        format="s16",
        layout="stereo",
        rate=audio_sample_rate,
        frame_size=int(audio_sample_rate * AUDIO_PTIME)
        )
    
    
    vFrame = VideoFrame(width=1280, height=720)
    vFrame.pts = 0
    vFrame.time_base = '1/90000'
    aFrame = AudioFrame(samples=960)
    aFrame.pts = 0
    aFrame.rate = 48000

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
            if isinstance(exc, StopIteration):
                container.seek(0)
                continue
            if cameraplayer.audioFrameBuffer:
                cameraplayer.audioFrameBuffer = aFrame
            if cameraplayer.videoFrameBuffer:
                cameraplayer.videoFrameBuffer = vFrame
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
                frame.time_base = audio_time_base
                audio_samples += frame.samples

                frame_time = frame.time
                # Put into buffer
                # print("Write to buffer: " + str(frame))
                
                # Figure out place in buffer and put
                if (cameraplayer.audioFrameBufferIndex > (len(cameraplayer.audioFrameBuffer) - 1)):
                    # If trying to write above buffer, eol!
                    # print("EOL")
                    cameraplayer.audioFrameBufferIndex = 0
                    cameraplayer.audioFrameBufferEOL = True
                    cameraplayer.audioFrameBuffer[cameraplayer.audioFrameBufferIndex] = frame
                elif (cameraplayer.audioFrameBufferIndex == 2):
                    # After 5 frames remove EOL
                    cameraplayer.audioFrameBuffer[cameraplayer.audioFrameBufferIndex] = frame
                    cameraplayer.audioFrameBufferEOL = False
                    cameraplayer.audioFrameBufferIndex += 1
                else:
                    # If no special condition
                    cameraplayer.audioFrameBuffer[cameraplayer.audioFrameBufferIndex] = frame
                    cameraplayer.audioFrameBufferIndex += 1
                    
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
            # Reformat frame to wanted width and height if above it
            if (frame.width > newWidth) or (frame.height > newHeight):
                frame = frame.reformat(width=newWidth, height=newHeight)
            # Put into buffer
            cameraplayer.videoFrameBuffer = frame
            