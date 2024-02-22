import os, sys, m3u8, datetime, av, asyncio, threading, time, queue, fractions, signal, shutil
# Because FFMPEG cannot write custom M3U8 tags, which I need so I can reference when the clip starts in absolute time,
# Since my timeline exporter needs to know when each file was written, it IS an nvr.
#
# If calculations are needed for space-storage allocations, found website works well (Use HIGH for each format): 
# https://www.cctvcalculator.net/en/calculations/storage-needs-calculator/
#
# ABOVE NO LONGER EXISTS, even though it was an amazing tool, this one works as well:
# https://www.westerndigital.com/tools/surveillance-capacity-calculator
#
# This file is basically an RTSP to m3u8 file converter, so it can be used outside of Zemond as well with a minor amount of modification!
global killSignal, frameQueueEmptyTracker

# Some basic settings below, including what video encoder to use (libx265 by default), and audio encoder.
directOutputToDockerLog = True # Also just STDOUT and STDERR, basically does script output text?
audioEncoderToUse = 'mp3' # Basic audio codec, nothing special
videoEncoderToUse = 'libx264' # Valid options: libx265, libx264, only use h265 if your browser supports it, Chrome should
formatContainerToUse = 'mpegts' # Livestreamable chunked format, so the browser can recall footage
formatContainerExtension = 'ts' # That chuncked format extension
frameQueueEmptyTracker = 0 # If we don't get a frame X amount of times, kill program

# When a SIGINT is detected, set the global killSignal to true so all functions and loops cease
def sigint_handler(sig, frame):
    global killSignal
    print("Unexpected SIGINT Received, exiting...")
    killSignal = True
    # Wait for 5 seconds, then kill main thread
    time.sleep(5)
    # Force exit, all code should be done by then
    sys.exit()

# Attempt to initialize variable function
def initEnvVariable(variableToSet):
    # Attempt to return enviroment variable data, if not exit program
    try:
        variableToSet = os.environ[str(variableToSet)]
        # print("DEBUG: SET VARIABLE DATA TO: " + str(variableToSet))
        return variableToSet
    except:
        print("FATAL: Could not set Enviroment Variable " + str(variableToSet) + "! Exiting...")
        sys.exit()

# Check for base storage directory, then return the cameraDirectory 
def directoryCheck(camera_name_env):
    # Check if /zemond-storage exists, user must create manually since it might be an abstracted mount!
    if not os.path.exists("/zemond-storage/"):
        print("FATAL: /zemond-storage/ does not exist! Needs to be created manually so the user can store it using any file system abstraction trickery desired. Exiting...")
        sys.exit()

    # Check if cameraDirectory exists, if not, create (/zemond-storage MUST exist)
    cameraDirectory = str("/zemond-storage/" + camera_name_env + '/')
    if not os.path.exists(cameraDirectory):
        os.makedirs(cameraDirectory)
        
    return cameraDirectory

# Get back m3u8 playlist object from on disk m3u8 file, if no file is found, create
def m3u8FileCheck(camera_name_env, cameraDirectory):
    # Create file name
    m3u8FileName = str(camera_name_env + '.m3u8')
    # Create absolute file path
    m3u8AbsolutePath = (cameraDirectory + m3u8FileName)
    # Create m3u8 playlist object, currently empty
    m3u8PlaylistObject = m3u8.M3U8()

    # If m3u8 does not exist, then create
    if not os.path.exists(m3u8AbsolutePath):
        # File does not exist, create new blank
        m3u8PlaylistObject.dump(m3u8AbsolutePath)
    else:
        # File must exist, load into m3u8PlaylistObject
        m3u8PlaylistObject = m3u8.load(m3u8AbsolutePath)
    
    # Return playlist object with data from disk
    return m3u8PlaylistObject

# Seperate threaded function to write RTSP frames to processing queues
def writeFramesToQueue(inputContainer, rtspFrameQueue):
    global killSignal
    try:        
        # For every incoming frame in rtspContainer
        for frame in inputContainer.decode():
            # Originally broke this if killSignal was detected, but broke parent thread when this broke! So just break parent thread and have this one exit naturally 
            # Write next frame to queue from inputContainer    
            rtspFrameQueue.put(frame)
            
    except Exception as e:
        print("Exception in writting to frame queue: " + str(e))
        pass
            
# Main thread function to write next frame in queue to output container
def writeFromQueueToContainerForSeconds(rtspFrameQueue, outputAudio, outputVideo, outputContainer, videoTimeBase, secondsToWrite, segmentWriting, m3u8Playlist, m3u8AbsolutePath):
    global killSignal, frameQueueEmptyTracker
    # Get start time for writing for secondsToWrite
    startTime = time.time()
    # For proper frame timing, using first frame PTS as reference
    firstAudioFramePTS = None
    firstVideoFramePTS = None
    
    # To get PTS information correct, we need to look at the difference (-) between this Frame and First frames PTS to determine what our current PTS should be, 
    # Since each container NEEDS the PTS reset for proper timing
    while True:
        # Check if killSignal is true
        if killSignal == True:
            # Safely close container, exit thread
            # Flush remianing packets to container
            remainPackets = outputVideo.encode(None)
            outputContainer.mux(remainPackets)
            # Close container
            outputContainer.close()
            # Make proper changes to m3u8
            
            # Get duration of container just written, set in segment
            durationEstimate = (time.time() - startTime)
            segmentWriting.duration = durationEstimate
            
            # Append to playlist object
            m3u8Playlist.segments.append(segmentWriting)
            
            # Write playlist object to disk
            with open(m3u8AbsolutePath, 'w') as file:
                file.write(m3u8Playlist.dumps())
            sys.exit()
               
        # CURRENT BUG
        # At seemingly random, frame buffer will not empty and last frame will be written over and over forever? Somehow??
        #
        # BUG FOUND: When encoder has no frames to give out when encoding None, it gives End Of File exception, solution
        # is to wrap this in a try statement
                
        # Try to encode latestFrame and write resulting packets to mp4
        try:
            # If we don't get a frame for 500 reads then assume RTSP pipe is broken and quit, supervisord will restart us
            if frameQueueEmptyTracker >= 500:
                
                myPid = os.getpid()
                os.kill(myPid, signal.SIGINT)
                # Wait for death
                time.sleep(10)
            
            # Wait 0.01 seconds for frame, keeps up fine
            time.sleep(0.01)
            # If the frame queue is empty, do not attempt read and add to counter
            if rtspFrameQueue.empty():
                # Add one to tracker
                frameQueueEmptyTracker += 1
            else:
                # Frame queue is not empty, reset fail read counter and grab frame to process
                frameQueueEmptyTracker = 0
                # Grab latest frame from queue
                latestFrame = rtspFrameQueue.get()
                # print("Latest frame: " + str(latestFrame))
                
                # Depending on frame grabbed, process diffrerently
                # AUDIO
                if isinstance(latestFrame, av.AudioFrame):
                    # Have audio frame, encode to mp3 audio and write to container
                    # PTS Reset code, first frame PTS from queue is set, then is used as offset for setting new containers PTS    
                    # if firstAudioFramePTS is None:
                        # Set first frame PTS
                        # firstAudioFramePTS = latestFrame.pts
                    
                    # Set this frames PTS to the offset of first frame (latestFrame.pts = latestFrame.pts - firstAudioFramePTS)
                    # latestFrame.pts -= firstAudioFramePTS
                    # print("New PTS: " + str(latestFrame.pts))
                    
                    # Encode frame to packet for muxxing into container
                    for packet in outputAudio.encode(latestFrame):
                        # print("Packet PTS: " + str(packet.pts))
                        outputContainer.mux(packet)
                
                # VIDEO      
                elif isinstance(latestFrame, av.VideoFrame):
                    # Have video frame, encode to h264 video and write to container   
                    # PTS Reset code, first frame PTS from queue is set, then is used as offset for setting new containers PTS     
                    # if firstVideoFramePTS is None:
                        # Set first frame PTS
                        # firstVideoFramePTS = latestFrame.pts
                    
                    # Set this frames PTS to the offset of first frame (latestFrame.pts = latestFrame.pts - firstVideoFramePTS)
                    # latestFrame.pts -= firstVideoFramePTS
                    # print("New PTS: " + str(latestFrame.pts))

                    # Encode frame to packet for muxxing into container
                    for packet in outputVideo.encode(latestFrame):
                        outputContainer.mux(packet)
                        
                # print("Time elapsed: " + str(time.time() - startTime))
                # Check if secondsToWrite have elapsed since start of write
                if time.time() - startTime >= secondsToWrite:
                    # print("Time above quota")
                    # Close current output container and return True to signal write has finished
                    # Flush remianing packets to container
                    # This can fail if remainPackets is None, wrap in try statement so if fails we can close media
                    try:
                        remainPackets = outputVideo.encode(None)
                        outputContainer.mux(remainPackets)
                    except Exception as e:
                        # print("Got exception in emptying encoder: " + str(e))
                        pass
        
                    # Segment length based on amount of time frames was written
                    durationEstimate = (time.time() - startTime)
                    segmentWriting.duration = durationEstimate
                    # Close container
                    outputContainer.close()
                    
                    
                    # Return true to break loop and show code completeled normally
                    return True
            
        # If any issues occur with encoding, just pass and continue      
        except Exception as e:
            # print("Got Exception!: " + str(e))
            pass
    
# Seperate function for main looping logic to run in seperate thread so that SIGINT can run properly
def mainLoopingLogic():
    global killSignal
    
     # Incoming frame queue to write to disk
    rtspFrameQueue = queue.Queue()
    
    # Get enviroment variables
    # Get camera name
    camera_name_env = initEnvVariable("CAMERA_NAME")
    
    # Get RTSP camera source
    RTSP_PATHS_CAM1_SOURCE = 'rtsp://127.0.0.1:8554/cam1'

    # Get retentionInDays
    retentionInDays = int(initEnvVariable("retentionInDays"))

    # Check if storage directory exists
    cameraDirectory = directoryCheck(camera_name_env)
        
    # Make sure m3u8 file exists, get playlist object in return (Should be populated if already exists)
    m3u8PlaylistObject = m3u8FileCheck(camera_name_env, cameraDirectory)
    
    # Now we have name variables, camDirectory and playlist object, what do?
    # Segment order should be in oldest to newest sequencial order, so it plays properly from m3u8 
    
    # Open RTSP Source and invdividual streams
    # Retry opening RTSP Source until we can
    while True:
        try:
            rtspSourceContainer = av.open(RTSP_PATHS_CAM1_SOURCE)
            break
        except Exception as e:
            time.sleep(0.5)
            pass
        
    templateVideo = rtspSourceContainer.streams.video[0]
    templateAudio = rtspSourceContainer.streams.audio[0]
    # Get info from streams
    
    # AUDIO
    audioSampleRate = templateAudio.codec_context.rate
    
    # VIDEO
    videoTimeBase = templateVideo.time_base
    videoWidth = templateVideo.codec_context.width
    videoHeight = templateVideo.codec_context.height
    videoFormat = templateVideo.codec_context.pix_fmt    
    videoAvgRate = templateVideo.average_rate

    
    # Start seperate thread that always writes to the rtspFrameQueue
    writeTask = threading.Thread(target=writeFramesToQueue, args=(rtspSourceContainer, rtspFrameQueue, ))
    writeTask.start()
    
    # Calculate retention period in seconds by multiplying retention days by seconds in a day (86400)
    retentionPeriodInSeconds = (retentionInDays * 86400)
    
    # Calculate maximum segments to meet retention quota by dividing total retention period in seconds by clip length (10 seconds)
    # For example if retention was one day clip quota would be 8,640 total 10 seconds clips
    maxSegmentsCalculated = (retentionPeriodInSeconds // 10)
    
    # FOR TESTING, FORCE TO BE X
    # maxSegmentsCalculated = 5
    
    # Playlist file absolute path
    m3u8FileName = str(camera_name_env + '.m3u8')
    m3u8AbsolutePath = (cameraDirectory + m3u8FileName)
    
    while True:        
        # Get latest playlist data from disk
        m3u8PlaylistObject = m3u8FileCheck(camera_name_env, cameraDirectory)

        # Find amount of segments exisiting in m3u8
        segmentAmount = 0
        for segment in m3u8PlaylistObject.segments:
            segmentAmount += 1
    
        # Three way logic below
        # First check, if segmentAmount is below maxSegmentsCalculated, start writing at segmentAmount (Includes 0 segments)
        if segmentAmount < maxSegmentsCalculated:
            # print("Playlist not full, starting at last segment!")
            # print("Current Segment amount: " + str(segmentAmount) + " | Max Segments: " + str(maxSegmentsCalculated))
            
            currentSegmentWriting = segmentAmount + 1
            
            # print("Writing segment: " + str(currentSegmentWriting))

            # Generate video path of video to write
            videoFileAbsolutePath = (cameraDirectory + (camera_name_env + '_'+ str(currentSegmentWriting) + '.' + formatContainerExtension))

            # Initialize output container
            outputContainer = av.open((videoFileAbsolutePath), mode='w', format=formatContainerToUse)
            # AUDIO
            outputAudio = outputContainer.add_stream(audioEncoderToUse, rate=44100)
            # VIDEO
            outputVideo = outputContainer.add_stream(videoEncoderToUse, rate=videoAvgRate, options={'x265-params': 'log_level=none'})
            outputVideo.width = videoWidth
            outputVideo.height = videoHeight
            outputVideo.pix_fmt = videoFormat
            outputVideo.time_base = videoTimeBase
                        
            # Create new segment object
            segment = m3u8.Segment(uri=videoFileAbsolutePath, duration=10)
            
            # Get start time for video, add to segment program_date_time, is tag EXT-X-PROGRAM-DATE-TIME
            segment.program_date_time = datetime.datetime.now()
            
            # Write video to disk using frames from rtspFrameQueue
            # print("Writing Video to disk!")
            writeFromQueueToContainerForSeconds(rtspFrameQueue, outputAudio, outputVideo, outputContainer, videoTimeBase, 10, segment, m3u8PlaylistObject, m3u8AbsolutePath)
            
            # File is done writing, make changes to playlist on disk and write to disk
            # print("Done writing to disk, change on disk m3u8")
            # Append to playlist object
            m3u8PlaylistObject.segments.append(segment)
            
            # Write playlist object to disk
            with open(m3u8AbsolutePath, 'w') as file:
                file.write(m3u8PlaylistObject.dumps())
                
        # If the playlist has met the segment quota, find the oldest segment by EXT-X-PROGRAM-DATE-TIME and grab URI to write to, and make newest segment
        elif segmentAmount == maxSegmentsCalculated:
            # print("Playlist is full!")
        
            # Based on EXT-X-PROGRAM-DATE-TIME, determine the oldest segment in the playlist
            
            # Tracking and determine vars
            oldestSegmentIndex = 0
            trackingSegmentIndex = 0
            for currentSegmentItteration in m3u8PlaylistObject.segments:
                # If current segment datetime is less then previous oldestSegment datetime, make new oldestSegment 
                if currentSegmentItteration.program_date_time < (m3u8PlaylistObject.segments[oldestSegmentIndex]).program_date_time:
                    oldestSegmentIndex = trackingSegmentIndex
                # Onto next segment for inspection
                trackingSegmentIndex += 1
            
            # DEBUG
            # print("End of loop, oldest segment is: " )
            # print(m3u8PlaylistObject.segments[oldestSegmentIndex])
            # print("URI Found: " + (m3u8PlaylistObject.segments[oldestSegmentIndex].uri))
            
            # Store that segments URI, delete that segment, and create new segment
            storedUriFromSegment = (m3u8PlaylistObject.segments[oldestSegmentIndex].uri)
            
            # Delete segment
            del m3u8PlaylistObject.segments[oldestSegmentIndex]
            
            # Write to disk
            with open(m3u8AbsolutePath, 'w') as file:
                file.write(m3u8PlaylistObject.dumps())
            
            # Start writing new segment
            # Initialize output container
            outputContainer = av.open((storedUriFromSegment), mode='w', format=formatContainerToUse)
            # AUDIO
            outputAudio = outputContainer.add_stream(audioEncoderToUse, rate=44100)
            # VIDEO
            outputVideo = outputContainer.add_stream(videoEncoderToUse, rate=videoAvgRate, options={'x265-params': 'log_level=none'})
            outputVideo.width = videoWidth
            outputVideo.height = videoHeight
            outputVideo.pix_fmt = videoFormat
            outputVideo.time_base = videoTimeBase
                        
            # Create playlist segment object
            segment = m3u8.Segment(uri=storedUriFromSegment, duration=10)
            
            # Get start time for video
            segment.program_date_time = datetime.datetime.now()
            
            # Write video to disk from queue
            # print("Writing Video to disk!")
            writeFromQueueToContainerForSeconds(rtspFrameQueue, outputAudio, outputVideo, outputContainer, videoTimeBase, 10, segment, m3u8PlaylistObject, m3u8AbsolutePath)            

            # print("Done writing to disk, change on disk m3u8")
            # Add segment to playlist object
            m3u8PlaylistObject.segments.append(segment)
            # Write to disk
            with open(m3u8AbsolutePath, 'w') as file:
                file.write(m3u8PlaylistObject.dumps())
            
        # If our quota is reduced, find the difference in segments, check for oldest segment and move file to segments-deleted, then delete segment
        elif segmentAmount > maxSegmentsCalculated:
            # This logic should only run if the user decreases the quota, say from 60 days to 30 days, 
            # No recording logic, should trim oldest 30 segments from file, move effected files into segments-deleted folder, 
            print("Above quota, move non-valid data to segments-deleted")
            
            # Check if segments-deleted, if not create
            segDelDirectory = cameraDirectory + 'segments-deleted/'
            if not os.path.exists(segDelDirectory):
                os.makedirs(segDelDirectory)
                
            # Calculate difference in segments, how many to 'delete'
            # segmentAmount will always be above maxSegments, but run through abs() just in case of negative number
            segmentAmountDiffrence = abs(segmentAmount - maxSegmentsCalculated)
            
            # Go through loop to delete all segments and move ajoining video file to segments-deleted
            currentSegmentDeleting = 0
            # While we are still trying to correct the segments to the quota
            while currentSegmentDeleting < segmentAmountDiffrence:
                # Next segment!  
                # Find new oldest segment, 
                # Based on EXT-X-PROGRAM-DATE-TIME, determine the oldest segment in the playlist

                # Tracking and determine vars
                oldestSegmentIndex = 0
                trackingSegmentIndex = 0
                for currentSegmentItteration in m3u8PlaylistObject.segments:
                    # If current segment datetime is less then previous oldestSegment datetime, make new oldestSegment 
                    if currentSegmentItteration.program_date_time < (m3u8PlaylistObject.segments[oldestSegmentIndex]).program_date_time:
                        oldestSegmentIndex = trackingSegmentIndex
                    # Onto next segment for inspection
                    trackingSegmentIndex += 1

                # Have oldest segment, get video URI, move video, then delete segment, write to disk
                moveURI = (m3u8PlaylistObject.segments[oldestSegmentIndex]).uri
                # Move file                
                shutil.move(moveURI, segDelDirectory)
                # Delete segment, write to disk
                del m3u8PlaylistObject.segments[oldestSegmentIndex]
                # Write playlist file to disk
                with open(m3u8AbsolutePath, 'w') as file:
                    file.write(m3u8PlaylistObject.dumps())
                
                # Continue with deleting old segments to meet quota
                currentSegmentDeleting += 1
    
    
# Start of program
if __name__ == '__main__':
    global killSignal
    
    # Set logging to stdout
    if directOutputToDockerLog == False:
        nullOutput = open(os.devnull, 'w')
        sys.stdout = nullOutput
        sys.stderr = nullOutput

    # Attempt to set logging, might have to just redirect STDOUT and STDERR to nothing or docker log...
    av.logging.set_level(av.logging.PANIC)
    
    # Make sure killSignal is false
    killSignal = False
    
    # Register unexpected SIGINT handler, so outputContainer closes properly, and other cleanup!
    # MUST do in main thread, as listener thread, so move main logic to seperated threaded function.
    signal.signal(signal.SIGINT, sigint_handler)
    signal.signal(signal.SIGTERM, sigint_handler)
    
    # Wait 5 seconds for RTSP server to start in docker container, then continue execution
    time.sleep(5)
    
    # Start seperate thread that runs main program, can properly handle SIGINT
    mainTask = threading.Thread(target=mainLoopingLogic)
    mainTask.start()