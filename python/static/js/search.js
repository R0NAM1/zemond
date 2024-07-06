var mouseDownScrubber = false;
var playOrPause = 'play';
var timeDuration = 0;
var leftSidePopped = true;
var srvUrl = null;
var videosLoading = 0;
var dynVidArray = []

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Also LLM generated, I have no shame.
function concatenateUint8Arrays(uint8arrays) {
    const totalLength = uint8arrays.reduce((total, uint8array) => total + uint8array.byteLength, 0);
    const result = new Uint8Array(totalLength);

    let offset = 0;
    uint8arrays.forEach((uint8array) => {
      result.set(uint8array, offset);
      offset += uint8array.byteLength;
    });

    return result.buffer; // Return the underlying ArrayBuffer
}

// Dynamic MediaSource based video player that can handle loading individual m4s's in an array sequecially.
class DynamicM4SVideoPlayer {
    // Make sure on every video.timeupdate event we should check if we need to load a new segment
    constructor(videoElement, segmentUrlArray, cameraName) {
        this.videoElement = videoElement;
        this.cameraName = cameraName;
        this.segmentUrlArray = segmentUrlArray;
        this.mediasource = new MediaSource();
        this.singleSourceBuffer = null; // Will be multiple MP4 files
        this.currentSegmentIndex = 0; // Current position in urlArray (Which MP4 are we playing?)
        this.totalDuration = (segmentUrlArray.length * 60) // Each segment is 60 seconds so easy calculation
        timeDuration = this.totalDuration;
        this.currentDownloadElement = null;
        this.fullDownloadLength = 0; // If anything but 0 then show loading screen
        this.progressBar = null;
        this.didMassPreload = false;
        // this.previousRate = 1;

        // Schedule video Event Listeners
        this.scheduleVideoEvents()

        // Call init
        this.initializeMediaSource()
    }

    async startLoadbar() {
        // Create custom loading element that goes over video element, make red square and text for now
        // Get video parent
        var videoDiv = this.videoElement.parentElement;
        videoDiv.style.position = 'relative'
        this.videoElement.style.zIndex = '1'
        
        var loadingScreen = document.createElement('div');
        
        loadingScreen.style.backgroundColor = 'rgba(97, 97, 97, 1)';
        loadingScreen.style.height = '100%';
        loadingScreen.style.width = '100%';
        loadingScreen.style.position = 'absolute'
        loadingScreen.style.top = '0'
        loadingScreen.style.left = '0'
        loadingScreen.style.zIndex = '2'
        loadingScreen.style.textAlign = 'center';
        loadingScreen.style.border = '5px solid rgb(0, 0, 0)';
        loadingScreen.style.boxSizing = 'border-box';

        // Stop user from interacting with timeline
        var bottomTimelineControlsParent = document.getElementById('bottomTimelineControlsParent')
        bottomTimelineControlsParent.style.pointerEvents = 'none'
        bottomTimelineControlsParent.style.opacity = '0.5'

        // Create inner elements
        var loadGif = document.createElement('img');
        loadGif.src = srvUrl;
        loadGif.style.width = '25%';
        loadGif.style.position = 'relative'
        loadGif.style.top = '25%'
        loadGif.style.zIndex = '-1'

        // Loading
        var totalBytes = document.createElement('h3');
        // Regex that I found online that adds commas to the thousand demoninator for nice looking numbers.
        // https://stackoverflow.com/questions/2901102/how-to-format-a-number-with-commas-as-thousands-separators
        totalBytes.innerText = (this.totalContentLength).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        totalBytes.className = 'downloadTotal'
        totalBytes.style.zIndex = '10'
        totalBytes.style.position = 'relative'

        this.currentDownloadElement = document.createElement('h3');
        this.currentDownloadElement.innerText = '0';
        this.currentDownloadElement.style.zIndex = '10'
        this.currentDownloadElement.style.position = 'relative'
        this.currentDownloadElement.style.width = 'auto'
        this.currentDownloadElement.style.transform = 'translateY(15px)';
        this.currentDownloadElement.style.display = 'inline-block'
        this.currentDownloadElement.style.margin = '0px'


        var fadeElement = document.createElement('div');
        fadeElement.style.position = 'relative'
        fadeElement.style.top = '25%'
        fadeElement.className = 'fadeElement'

        // Create progress bar
        this.progressBar = document.createElement('div');
        var progressBarProgress = document.createElement('div');

        this.progressBar.className = 'progressBar';
        progressBarProgress.className = 'progressBarProgress';
        progressBarProgress.style.width = '0px';

        this.progressBar.appendChild(progressBarProgress)


        fadeElement.appendChild(loadGif)
        loadingScreen.appendChild(fadeElement)
        loadingScreen.appendChild(this.currentDownloadElement)
        loadingScreen.appendChild(totalBytes)
        loadingScreen.appendChild(this.progressBar)
        videoDiv.appendChild(loadingScreen)
        return loadingScreen;
    }

    async stopLoadbar(loadingScreen) { 
        this.videoElement.poster = "";
        loadingScreen.remove()

        // Check if videosLoading is 0, if so then allow user to interact with timeline
        if (videosLoading == 0) {
            var bottomTimelineControlsParent = document.getElementById('bottomTimelineControlsParent')
            bottomTimelineControlsParent.style.pointerEvents = 'all'
            bottomTimelineControlsParent.style.opacity = '1'
        }
    }

    async downloadFileWithProgress(url) {
        console.log(this.cameraName + " | Fetching: ", url)
        while (true) {
            try {

                videosLoading = videosLoading + 1;

                var fileResponse = await fetch(url);

                if (!fileResponse.ok) {
                    throw new Error(`HTTP error status: ${fileResponse.status}`);
                }

                this.totalContentLength = Number(fileResponse.headers.get('Content-Length'));

                const reader = fileResponse.body.getReader();

                let receivedLength = 0;
                let receviedBytesArray = [];

                let loadingScreen = await this.startLoadbar();

                while (true) {
                    const { done, value } = await reader.read();

                    if (done) {
                        videosLoading = videosLoading - 1;
                        await this.stopLoadbar(loadingScreen);
                        return concatenateUint8Arrays(receviedBytesArray);
                    }

                    receviedBytesArray.push(value);
                    receivedLength += value.length;
                    this.currentDownloadElement.innerText = (receivedLength).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");

                    // Calc percent and update progress bar
                    var percentLoaded = (receivedLength / this.totalContentLength) * 100;
                    (this.progressBar.firstChild).style.width = percentLoaded + '%';
                }

            }
            
            catch (error) {
                console.error(this.cameraName + ` | Fetch failed, retrying: ${error.message}`);
                await sleep(3000)
            }
        }
    }

    initializeMediaSource() {
        // Set mediasource to be videoElement source
        this.videoElement.src = URL.createObjectURL(this.mediasource);
        // If ms is opened, add source buffer codec info & load segment into buffer
        
        this.mediasource.addEventListener('sourceopen', async () => {
            this.mediasource.duration = this.totalDuration;
            // Determine video codec with MP4Box
            const mp4boxFile = new MP4Box.createFile();
            // mp4boxjs logging
            // Log.setLogLevel(Log.debug);
            while (true) {
                try {
                    var fetchedM4SData = await this.downloadFileWithProgress(this.segmentUrlArray[0]);
                    break;
                } catch (e) {
                    console.log(this.cameraName + " | Error fetching " + this.segmentUrlArray[0] + " , retrying in 3 seconds...")
                    await sleep(3000);
                }
            }

            fetchedM4SData.fileStart = 0;
            mp4boxFile.appendBuffer(fetchedM4SData);

            var sourceCodec = mp4boxFile.getInfo().mime;
            console.info(this.cameraName + " | Downloaded Media Codec is: ", sourceCodec);

            this.singleSourceBuffer = this.mediasource.addSourceBuffer(sourceCodec);
            this.singleSourceBuffer.mode = ("sequence");

            // Manually load downloaded segment into segment
            // If the buffer is updating then wait until the update is ended
            if (this.singleSourceBuffer.updating) {
                console.log(this.cameraName + " | Buffer is updating, waiting for updateend")
                await new Promise(resolve => this.singleSourceBuffer.addEventListener('updateend', resolve, { once: true }));
                console.log(this.cameraName + " | updateend received, continuing.")
            }

            // Append new data to buffer, should fill whereever we need it to
            this.singleSourceBuffer.timestampOffset = 0;
            this.singleSourceBuffer.appendBuffer(fetchedM4SData);

            ///////////

            this.singleSourceBuffer.addEventListener("updateend", () => {
                console.log(this.cameraName + ' | Added or removed Buffer, new times: ', this.singleSourceBuffer.buffered);
            });

            await this.preloadNextSegment(this.currentSegmentIndex);
        });

        ////////////////////////
        // If mediasource ends, cleanup (Figure out later)
        this.mediasource.addEventListener('sourceended', () => {
            this.singleSourceBuffer.remove(0, (this.segmentUrlArray.length * 60))
            console.log(this.cameraName + ' | MediaSource ended');
        });

    }

    // Switch segment by unloading previous segment in memory (10mb each minute!) and then loading a segment (For when user seeks)
    async switchSegmentSeeked(newIndex) {
        if (newIndex < 0 || newIndex >= this.segmentUrlArray.length) {
            console.warn(this.cameraName + ' | Invalid segment index');
            return;
        }
        
        // Remove old filled part of buffer
        const startTime = this.currentSegmentIndex * 60;
        const endTime = (this.currentSegmentIndex + 1) * 60;
        console.log(this.cameraName + " | Switching Segment, first removing 0 to " + this.totalDuration);
        await this.singleSourceBuffer.remove(0, this.totalDuration);

        // Set time offset
        this.mediasource.timestampOffset = startTime;

        // Update index and reload
        this.currentSegmentIndex = newIndex;
        await this.loadSegment(newIndex, newIndex * 60);
        // If not final index, preload next segment
        if (newIndex < (this.segmentUrlArray.length - 1)) {

            if (this.videoElement.playbackRate >= 4) {
            //     // Preload 5 segments
                await this.preloadNextSegment(newIndex);
                await this.preloadNextSegment(newIndex + 1);
            //     await this.preloadNextSegment(newIndex + 2);
            //     await this.preloadNextSegment(newIndex + 3);
            //     await this.preloadNextSegment(newIndex + 4);
            }
            else {
                // Preload next segment
            await this.preloadNextSegment(newIndex);
            }
        }
    }

    // Switch segment by unloading all in memory preloading next segment (For seemless crossover)
    async switchSegmentSeemless(newIndex) {
        if (newIndex < 0 || newIndex >= this.segmentUrlArray.length) {
            console.warn(this.cameraName + ' | Invalid segment index');
            return;
        }
        
        // Remove old filled part of buffer
        const startTime = this.currentSegmentIndex * 60;
        const endTime = (this.currentSegmentIndex + 1) * 60;
        console.log(this.cameraName + " | Switching Segment, first removing " + startTime + " to " + endTime);
        await this.singleSourceBuffer.remove(0, endTime);


        // If playbackRate was below 4 then preload extra segment
        // if (this.previousRate < 4 && this.videoElement.playbackRate >= 4) {
        //     console.log("Speed above 4, preloading extra segments!")
        //     await this.preloadNextSegment(newIndex);
        //     await this.preloadNextSegment(newIndex + 1);
        // }


        this.previousRate = this.videoElement.playbackRate;

        // Update index and reload
        this.currentSegmentIndex = newIndex;
        // await this.loadSegment(this.currentSegmentIndex + 1, startTime);
        // If not final index, preload next segment
        if (newIndex < (this.segmentUrlArray.length - 1)) {
            // if (this.videoElement.playbackRate >= 4) {
            //     // Preload 5 segments
            //     await this.preloadNextSegment(newIndex + 2);
            //     // await this.preloadNextSegment(newIndex + 3);
            //     // await this.preloadNextSegment(newIndex + 4);
            // }
            // else {
                // Preload next segment
            await this.preloadNextSegment(newIndex);
            // }
        }
    }

    // Append current segment in singleSourceBuffer, does not delete old segment. Use on init & switchSegment
    async loadSegment(index, startTime) {
        try {
            console.log(this.cameraName + " | Loading new segment at index " + index);

            this.videoElement.pause()

            this.didMassPreload = false;

            // Set pause button to be paused
            var cameraTableTH = document.getElementById('cameraTableTH');
            var playButtonElement = document.getElementById('playButtonElement');
            cameraTableTH.innerText = "Play";
            playButtonElement.src = "/static/playButton.png";
            playOrPause = 'play'

            var fetchedM4SData = null;

            while (true) {
                try {
                    fetchedM4SData = await this.downloadFileWithProgress(this.segmentUrlArray[index]);
                    // fetchedM4SData = await fetchedM4SFile.arrayBuffer();
                    console.log(this.cameraName + " | Fetched " + this.segmentUrlArray[index])
                    break;
                } catch (e) {
                    console.log(this.cameraName + " | Error fetching " + this.segmentUrlArray[index] + " , retrying...")
                    await sleep(3000);
                }
            }
            fetchedM4SData.fileStart = 0;

            // If the buffer is updating then wait until the update is ended
            if (this.singleSourceBuffer.updating) {
                console.log(this.cameraName + " | Buffer is updating, waiting for updateend")
                await new Promise(resolve => this.singleSourceBuffer.addEventListener('updateend', resolve, { once: true }));
                console.log(this.cameraName + " | updateend received, continuing.")
            }

            // Append new data to buffer, should fill whereever we need it to
            this.singleSourceBuffer.timestampOffset = startTime;
            this.singleSourceBuffer.appendBuffer(fetchedM4SData);

            // Data is appended, reflect buffer in timeline with green
            var thD = document.getElementById('thD' + index);
            // Make below cells glow

            var allBelow = document.getElementsByClassName('dC' + index)
            
            // thD

            for (var element of allBelow) {
                console.log(element)
                element.style.backgroundColor = 'rgb(25, 180, 0)';
            }

            // Set timestampOffset based on startTime

            this.currentSegmentIndex = index;
        }
        catch(error) {
            console.error(this.cameraName + ' | Error loading segment:', error);
        }
    }

    // Modified loadSegment to preload and append
    // Current preload 5 segments, just to cover all cases, we have te RAM!
    async preloadNextSegment(index) {
        // if this.didMassPreload is false, go into loop and preload next 5 segments, if true just preload the 5th
        index = index + 1

        var preloadAmount = 2
        
        if (this.didMassPreload == false) {
            var tt = 0;
            while (tt < preloadAmount) {
                try {
                    console.log((this.cameraName + " | Preloading segment at index " + (index + tt) + ", "), this.segmentUrlArray[index + tt]);
                    var fetchedM4SFile = await fetch(this.segmentUrlArray[index + tt]);
                    var fetchedM4SData = await fetchedM4SFile.arrayBuffer();
                    fetchedM4SData.fileStart = 0;
        
                    // If the buffer is updating then wait until the update is ended
                    if (this.singleSourceBuffer.updating) {
                        console.log(this.cameraName + " | Buffer is updating, waiting for updateend")
                        await new Promise(resolve => this.singleSourceBuffer.addEventListener('updateend', resolve, { once: true }));
                        console.log(this.cameraName + " | updateend received, continuing.")
                    }
        
                    // Append new data to buffer, should fill whereever we need it to
                    this.singleSourceBuffer.appendBuffer(fetchedM4SData);
                        console.log((this.cameraName + " | Sucessfully Preloaded segment."));
                    }
                    catch(error) {
                        console.error(this.cameraName + ' | Error loading segment:', error);
                    }

                    tt++;
            }
            this.didMassPreload = true;
        }
        else {

            try {
                index = index + (preloadAmount - 1)
                console.log((this.cameraName + " | Preloading segment at index " + index + ", "), this.segmentUrlArray[index]);
                var fetchedM4SFile = await fetch(this.segmentUrlArray[index]);
                var fetchedM4SData = await fetchedM4SFile.arrayBuffer();
                fetchedM4SData.fileStart = 0;
    
                // If the buffer is updating then wait until the update is ended
                if (this.singleSourceBuffer.updating) {
                    console.log(this.cameraName + " | Buffer is updating, waiting for updateend")
                    await new Promise(resolve => this.singleSourceBuffer.addEventListener('updateend', resolve, { once: true }));
                    console.log(this.cameraName + " | updateend received, continuing.")
                }
    
                // Append new data to buffer, should fill whereever we need it to
                this.singleSourceBuffer.appendBuffer(fetchedM4SData);
                console.log((this.cameraName + " | Sucessfully Preloaded segment."));
    
                }
                catch(error) {
                    console.error(this.cameraName + ' | Error loading segment:', error);
                }
        }

    }

    scheduleVideoEvents() { 
        // Everytime the video time changes determine what and what 
        this.videoElement.addEventListener('timeupdate', () => {
            // Calculate segment we should load, determine if a new one. Round down.
            var computedSegment = Math.floor(this.videoElement.currentTime / 60);
            // Debug
            // console.warn(this.cameraName + " | Current Segment:", this.currentSegmentIndex)
            // console.warn(this.cameraName + " | Computed Segment:", computedSegment)
            // console.warn(this.cameraName + " | Array Length:", this.segmentUrlArray.length)

            // Check if computed index is size of available array, then we are at end, do not switch!
            if (computedSegment == this.segmentUrlArray.length) {
                var cameraTableTH = document.getElementById('cameraTableTH');
                var playButtonElement = document.getElementById('playButtonElement');
                cameraTableTH.innerText = "Play";
                playButtonElement.src = "/static/playButton.png";
                playOrPause = 'play'
                console.log(this.cameraName + " | Video is at end!")
            }

            // If the video moves into a new segment naturally, removing old segment
            else if (computedSegment == this.currentSegmentIndex + 1) {
                console.warn(this.cameraName + " | Old segment flowed into new segment, switching!")
                this.switchSegmentSeemless(computedSegment);
            }
   
            // If user seeks then remove all in buffer and load as in new.
            // else if ((computedSegment !== this.currentSegmentIndex) && (computedSegment !== (this.currentSegmentIndex + 1))) {
            // }
        });

        this.videoElement.addEventListener('error', (e) => {
            console.error('Video Element Error: ', e.target.error)
        });

        this.videoElement.addEventListener('waiting', async () => {
            var computedSegment = Math.floor(this.videoElement.currentTime / 60);
            console.log('Video is waiting for more data.', computedSegment);
            // await sleep(500);
            // Go through all Video Players and regrab data
            var hlsVideoElements = document.getElementsByClassName('hlsContainer');

            
            cameraTableTH.innerText = "Play";
            // Loop over each video, pause each
            for (var container of hlsVideoElements) {
                container.pause();
            }
            
            
            playButtonElement.src = "/static/playButton.png";
            playOrPause = 'play'

            this.switchSegmentSeeked(computedSegment)
            
            // for (var dynVid of dynVidArray) {
                // dynVid.switchSegmentSeeked(computedSegment);
            // }

            

        });

        this.videoElement.addEventListener('stalled', async () => {
            console.log(this.cameraName + ' | Video playback has stalled.');
        });

        this.videoElement.addEventListener('seeking', async () => {
            // Set playbutton to download symbol to show we need to grab new data.
            var cameraTableTH = document.getElementById('cameraTableTH');
            var playButtonElement = document.getElementById('playButtonElement');
            cameraTableTH.innerText = "Load Segment";
            playButtonElement.src = "/static/downloadButton.png";
            playOrPause = 'play'
          });
    }

}

////////////////////////////////////////////

function addCameraItemDiv(cameraname) {
    // Select parent element
    var parentDiv = document.getElementById('step1selectcameras');

    // Create encompassing div
    var outsideDiv = document.createElement('div');
    outsideDiv.className = 'selectCameraItem';
    // Create inner label
    var innerLabal = document.createElement('label')
    // Create checkbox element
    var innerCheckbox = document.createElement('input');
    innerCheckbox.type = 'checkbox';
    // Create text node
    var labelTextNode = document.createTextNode(cameraname);

    // Append checkbox to label
    innerLabal.appendChild(innerCheckbox);
    
    // Set text content
    innerLabal.appendChild(labelTextNode);
    // Append innerLabel to outsideDiv
    outsideDiv.appendChild(innerLabal);
    // Append outsideDiv to parentDiv
    parentDiv.appendChild(outsideDiv);
}

// This function expects an array of m3u8 strings so it can work
// Set array limit to 9, since that's what works best with the display
export function generateVideoTray(m3u8StringArray, camListArray) {   
    var videoContainer = document.getElementById('videoContainer');
    var gridRows = 0;
    var gridColumns = 0;

    // Artifically pad array for testing
    // var tt = 1;
    // while (tt <= 5) {
    //     m3u8VideoObjects.push('tt');
    //     tt = tt + 1
    // }

    
    // Allow playback speed
    var playBackSpeedSelectElement = document.getElementById('playBackSpeedSelect');
    
    playBackSpeedSelectElement.style.opacity = '1';
    playBackSpeedSelectElement.style.pointerEvents = 'auto';
    
    // First, remove all elements in videoContainer
    videoContainer.innerHTML = '';   
    
    // Based on length of array, set CSS settings for container
    
    if (m3u8StringArray.length <= 2) {
        gridColumns = m3u8StringArray.length;
        gridRows = 1;
    } 
    else {
        gridColumns = Math.ceil(Math.sqrt(m3u8StringArray.length))
        gridRows = Math.ceil(m3u8StringArray.length / gridColumns)
    }
    
    // Final CSS settings
    videoContainer.style.gridTemplateColumns = (`repeat(${gridColumns}, 1fr)`);
    videoContainer.style.gridTemplateRows = (`repeat(${gridRows}, 1fr)`);
    
    // Reset dynVidArray
    dynVidArray = []

    // For length of array, add amount of video containers with class hlsContainer
    var m3u8Index = 0;
    for (var m3u8Urls of m3u8StringArray) {
        // Edit m3u8 string to include server URL
        var loc = window.location;
        var hostFullName = (loc.protocol + '//' + loc.hostname + ':' + loc.port)
        m3u8Urls = m3u8Urls.replaceAll("/search/", hostFullName + "/search/")
        
        // Convery m3u8Urls string to array
        var m3u8UrlArray = m3u8Urls.split("*");
        
        // Generate video element 
        var thisVideoElement = document.createElement('video')
        thisVideoElement.poster = '/static/poster.png'
        // Video Contain Element
        var thisVideoElementDiv = document.createElement('div');
        
        // Set options
        // Mute by default
        thisVideoElement.muted = true;

        // Set CSS options
        // thisVideoElement.style.position = 'absolute';
        thisVideoElement.style.height = 'auto';
        thisVideoElement.style.width = '100%';
        // thisVideoElement.style.transform = 'translate(-125px, 0)'       
        thisVideoElement.style.objectFit = 'contain';
        thisVideoElement.controls = false;

        // If m3u8VideoObjects.length is 1, then change specific CSS,
        if (m3u8StringArray.length == 1) {
            thisVideoElement.style.height = '70vh';
            thisVideoElement.style.width = '100%';
        } 

        // Set class
        thisVideoElement.className = 'hlsContainer';

        // Add video to container
        thisVideoElementDiv.appendChild(thisVideoElement)
        videoContainer.appendChild(thisVideoElementDiv);

        // Attatch new DynamicM4SVideoPlayer
        var dynVid = new DynamicM4SVideoPlayer(thisVideoElement, m3u8UrlArray, camListArray[m3u8Index]);
        dynVidArray.push(dynVid)

        m3u8Index = m3u8Index + 1;
    }

    
    // At end, now set playback rate to current selection
    var playBackSpeedSelectElement = document.getElementById('playBackSpeedSelect');    
    var newPlayBackSpeed = Number((playBackSpeedSelectElement.value).replace('x', ''))
    
    var hlsVideoElements = document.getElementsByClassName('hlsContainer');


    // Apply to all videos
    for (var container of hlsVideoElements){
        container.playbackRate = newPlayBackSpeed;
    }

}

export function generateTimelineEmpty(fromDate, toDate, camListArray){
    // Generate scrubber timeline to syncronize all hlsContainer class video objects
    // This MUST be run before motion event data is requested since elements won't exist

    fromDate = new Date(fromDate);

    var bottomTimelineControls = document.getElementById('bottomTimelineControls');
    var playerControls = document.getElementById('playerControls');
    // Reset bottomTimelineControls
    bottomTimelineControls.innerHTML = '';
    bottomTimelineControls.style.overflowY = 'auto';
    bottomTimelineControls.style.scrollbarWidth = 'none';
    bottomTimelineControls.style.overflowX = 'hidden';
    playerControls.innerHTML = '';
    playerControls.style.height = '155px';
    playerControls.style.transform = 'translateY(636px)';
    
    // Create camera names, scrub box and scrub handle
    var cameraNameTable = document.createElement('table');
    cameraNameTable.style.position = 'relative';
    cameraNameTable.id = 'cameraNameTable';
    cameraNameTable.style.padding = '0';
    cameraNameTable.style.borderCollapse = 'separate';
    cameraNameTable.style.borderSpacing = '0';
    cameraNameTable.style.tableLayout = 'fixed';
    cameraNameTable.style.width = '100%';
    
    
    var tr = document.createElement('tr');
    tr.id = 'headRow';
    var th = document.createElement('th');
    // Create amount of segments that exist according to array length
    
    th.id = "cameraTableTH"
    
    th.style.height = '30px'
    tr.style.position = 'sticky'
    tr.style.top = '0';
    tr.style.zIndex = '99';
    tr.appendChild(th);
    
    var numSeggs = Math.floor(timeDuration / 60);
    // Limit to 300 as it gets so squished beyond that you can't see anything, dosen't matter if it's accurite, 
    if (numSeggs > 300) {
        numSeggs = 300
    }
    
    // Correct time difference
    fromDate.setSeconds(fromDate.getSeconds() - 60)
    
    
    var trackS = 0;
    
    while (trackS < (numSeggs)) {
        let thD = document.createElement('th');
        fromDate.setSeconds(fromDate.getSeconds() + 60)
        
        // Extracting date and time components
        let month = fromDate.getMonth() + 1; // Adding 1 to account for zero-based indexing
        let day = fromDate.getDate();
        let year = fromDate.getFullYear();
        let hours = fromDate.getHours();
        let minutes = fromDate.getMinutes();
        
        // Formatting the date and time components into a string
        let formattedDate = `${month}/${day}/${year} - ${hours}:${minutes < 10? '0' : ''}${minutes}`;
        
        thD.addEventListener('mouseover', () => {
            var cameraTableTH = document.getElementById('cameraTableTH');
            if (numSeggs >= 300) {
                cameraTableTH.innerText = "Timeline to dense";
            }
            else {
                cameraTableTH.innerText = formattedDate;
            }
            
            // Make below cells glow
            var index = (thD.id).replace('thD', '');

            var allBelow = document.getElementsByClassName('dC' + index)
            
            for (var element of allBelow) {
                element.style.backgroundColor = '#3350a1';
            }
        });
        
        thD.addEventListener('mouseout', () => {
            var cameraTableTH = document.getElementById('cameraTableTH');
            cameraTableTH.innerText = '';
            
            // Make below cells glow
            var index = (thD.id).replace('thD', '');
            
            var allBelow = document.getElementsByClassName('dC' + index)
            
            for (var element of allBelow) {
                element.style.backgroundColor = '#797979';
            }
        });
        
        thD.className = "dataColumnHeader"
        thD.id = 'thD' + trackS
        thD.style.position = 'relative';
        // thD.appendChild(thTooltip);
        tr.appendChild(thD)
        trackS = trackS + 1
    }
    
    cameraNameTable.appendChild(tr);  
        
    // Create rows to put in tbody
    for (var camera of camListArray) {
        var tRow = document.createElement('tr');
        tRow.className = 'cameraTableTR';
        tRow.style.textAlign = 'center';
        var camnameColumn = document.createElement('td');
        camnameColumn.className = "cameraTableTD";
    camnameColumn.style.paddingUp = '0';
    camnameColumn.style.paddingDown = '0';
    camnameColumn.style.paddingLeft = '13px'
    camnameColumn.style.paddingRight = '13px';
    camnameColumn.style.overflowWrap = 'normal'
    camnameColumn.style.width = '200%'
    camnameColumn.innerText = camera;
    tRow.appendChild(camnameColumn)


    trackS = 0;

        while (trackS < numSeggs) {
            var dataColumn = document.createElement('td');
            dataColumn.classList.add("dataColumn")
            dataColumn.classList.add('dC' + trackS)
            
            trackS = trackS + 1
            tRow.appendChild(dataColumn)
        }

    cameraNameTable.appendChild(tRow)
    }


    var tableDiv = document.createElement('div');
    tableDiv.style.position = 'relative';
    tableDiv.id = 'tableDiv'
    tableDiv.appendChild(cameraNameTable)
    bottomTimelineControls.appendChild(tableDiv);
    
    var thD0 = document.getElementById('thD0');
    cameraNameTable = document.getElementById('cameraNameTable');
    cameraNameTable.style.width = 'calc(100% + ' + thD0.getBoundingClientRect().width + 'px)';
    
    // Create control box
    var controlBox = document.createElement('div');
    controlBox.style.position = 'relative'
    controlBox.style.display = 'grid';
    
    
    var scrubHandle = document.createElement('div');
    scrubHandle.id = 'scrubHandle';
    scrubHandle.style.left = '10%';
    

    var scrubHandleTringle = document.createElement('div');
    scrubHandleTringle.id = 'scrubHandleTringle';
    
    
    var tableDiv = document.getElementById('tableDiv');
    var headRow = document.getElementById('headRow');
    
    headRow.appendChild(scrubHandleTringle)
    tableDiv.appendChild(scrubHandle)    
    
    // Register event handlers to handle the scrubber setting time on videos
    // If mousedown on videoScrubber, then we can move it
    scrubHandle.addEventListener('mousedown', (e) => {
        e.preventDefault();
            // Set mouseDownScrubber to true
            mouseDownScrubber = true;
            // var scrubHandle = document.getElementById('scrubHandle');
            // var scrubHandleTringle = document.getElementById('scrubHandleTringle');
            // scrubHandle.style.backgroundColor = '#7592e0'
            // scrubHandleTringle.style.borderTop = '15px solid #7592e0'
    });
    scrubHandleTringle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        // Set mouseDownScrubber to true
        mouseDownScrubber = true;
        // var scrubHandle = document.getElementById('scrubHandle');
        // var scrubHandleTringle = document.getElementById('scrubHandleTringle');
        // scrubHandle.style.backgroundColor = '#7592e0'
        // scrubHandleTringle.style.borderTop = '15px solid #7592e0'
    });
    // Highlight on hover
    scrubHandle.addEventListener('mouseover', (e) => {
        e.preventDefault();
        var scrubHandle = document.getElementById('scrubHandle');
        var scrubHandleTringle = document.getElementById('scrubHandleTringle');
        scrubHandle.style.backgroundColor = '#7592e0'
        scrubHandleTringle.style.borderTop = '15px solid #7592e0'
            
    });
    scrubHandleTringle.addEventListener('mouseover', (e) => {
        e.preventDefault();
        var scrubHandle = document.getElementById('scrubHandle');
        var scrubHandleTringle = document.getElementById('scrubHandleTringle');
        scrubHandle.style.backgroundColor = '#7592e0'
        scrubHandleTringle.style.borderTop = '15px solid #7592e0'
    });
    scrubHandle.addEventListener('mouseout', (e) => {
        e.preventDefault();
        if (mouseDownScrubber == false) {
            var scrubHandle = document.getElementById('scrubHandle');
            var scrubHandleTringle = document.getElementById('scrubHandleTringle');
            scrubHandle.style.backgroundColor = 'black'
            scrubHandleTringle.style.borderTop = '15px solid black'
        }
            
    });
    scrubHandleTringle.addEventListener('mouseout', (e) => {
        e.preventDefault();
        if (mouseDownScrubber == false) {
            var scrubHandle = document.getElementById('scrubHandle');
            var scrubHandleTringle = document.getElementById('scrubHandleTringle');
            scrubHandle.style.backgroundColor = 'black'
            scrubHandleTringle.style.borderTop = '15px solid black'
        }
    });

    // If mouseup, we are for sure not mouse down on scrubber
    document.addEventListener('mouseup', (e) => {
        // Set mouseDownScrubber to false
        mouseDownScrubber = false;
    });

    // ////////////////////////// Buttons
    // Create play / pause button
    var playButtonElement = document.createElement('img');
    playButtonElement.style.width = "48px";
    playButtonElement.style.height = "48px";
    playButtonElement.src = "/static/playButton.png";
    playButtonElement.style.left = '0';
    playButtonElement.style.position = 'relative';
    playButtonElement.style.cursor = 'pointer';
    playButtonElement.style.borderBottom = '2px solid black';
    playButtonElement.style.paddingTop = '0px';
    playButtonElement.style.paddingBottom = '2px';
    playButtonElement.style.paddingLeft = '4px';
    playButtonElement.style.paddingRight = '8px';
    playButtonElement.id = 'playButtonElement';
    playButtonElement.addEventListener('mouseover', () => {
        
        var cameraTableTH = document.getElementById('cameraTableTH');
        
        if (playOrPause == 'play') {
            cameraTableTH.innerText = "Play";
        }
        else {
            cameraTableTH.innerText = "Pause";
        }
    });
    
    playButtonElement.addEventListener('mouseout', () => {
        var cameraTableTH = document.getElementById('cameraTableTH');
        cameraTableTH.innerText = '';
    });

    controlBox.appendChild(playButtonElement);

    // Create select button
    var selectButtonElement = document.createElement('img');
    selectButtonElement.style.width = "48px";
    selectButtonElement.style.height = "48px";
    selectButtonElement.src = "/static/selectButton.png";
    selectButtonElement.style.left = '0';
    selectButtonElement.style.position = 'relative';
    selectButtonElement.style.cursor = 'pointer';
    selectButtonElement.style.borderBottom = '2px solid black';
    selectButtonElement.style.paddingTop = '0px';
    selectButtonElement.style.paddingBottom = '2px';
    selectButtonElement.style.paddingLeft = '4px';
    selectButtonElement.style.paddingRight = '8px';
    selectButtonElement.id = 'selectButtonElement';
    selectButtonElement.addEventListener('mouseover', () => {

        var cameraTableTH = document.getElementById('cameraTableTH');
        
        cameraTableTH.innerText = "Reselect";
    });
    
    selectButtonElement.addEventListener('mouseout', () => {
        var cameraTableTH = document.getElementById('cameraTableTH');
        cameraTableTH.innerText = '';
    });
    
    controlBox.appendChild(selectButtonElement);

    // Create export button
    var exportButtonElement = document.createElement('img');
    exportButtonElement.style.width = "48px";
    exportButtonElement.style.height = "48px";
    exportButtonElement.src = "/static/exportButton.png";
    exportButtonElement.style.left = '0';
    exportButtonElement.style.position = 'relative';
    exportButtonElement.style.cursor = 'pointer';
    exportButtonElement.style.paddingTop = '2px';
    exportButtonElement.style.paddingBottom = '0px';
    exportButtonElement.style.paddingLeft = '4px';
    exportButtonElement.style.paddingRight = '8px';
    exportButtonElement.id = 'exportButtonElement';
    exportButtonElement.addEventListener('mouseover', () => {

        var cameraTableTH = document.getElementById('cameraTableTH');
        
        cameraTableTH.innerText = "Export";
    });
    
    exportButtonElement.addEventListener('mouseout', () => {
        var cameraTableTH = document.getElementById('cameraTableTH');
        cameraTableTH.innerText = '';
    });
    controlBox.appendChild(exportButtonElement);    
    playerControls.appendChild(controlBox)

    // Grab all video elements
    var hlsVideoElements = document.getElementsByClassName('hlsContainer');
    
    // Add event listen to listen for click, if so then press play on all video elements and based on first video in index, move custom scrubber
    playButtonElement.addEventListener('click', async (e) => { 
        

        var cameraTableTH = document.getElementById('cameraTableTH');
        
        if (playOrPause == 'play') {
            var computedSegment = Math.floor(hlsVideoElements[0].currentTime / 60);

            // If user manually seeked and presses play, then load segment
            if (computedSegment == dynVidArray[0].currentSegmentIndex) {
                
                cameraTableTH.innerText = "Pause";
                // Loop over each video, pause each
                for (var container of hlsVideoElements) {
                    container.play();
                }
                
                
                playButtonElement.src = "/static/pauseButton.png";
                playOrPause = 'pause'
                
            }
            else {
                console.log("User must have seeked, switching segment to ", computedSegment)
                for (var dynVid of dynVidArray) {
                    dynVid.switchSegmentSeeked(computedSegment);
                }
            }
        
            // Add event listener to update current scrubber
            hlsVideoElements[0].addEventListener('timeupdate', timeUpdateListener);
        
        }
        else if (playOrPause == 'pause') {

            cameraTableTH.innerText = "Play";
            playButtonElement.src = "/static/playButton.png";
            playOrPause = 'play'


            // Play each video
            for (var container of hlsVideoElements) {
                container.pause();
            }

            // Remove all event listener for hlsVideoElements[0]
            hlsVideoElements[0].removeEventListener('timeupdate', timeUpdateListener)
        }

    });


    //////////////////////////////////////////////////////////////////////////////////

    // Event listen on mousemove to check if mouseDownScrubber is true, if so we can move in the bounding boxes
    document.addEventListener('mousemove', (e) => {
        if (mouseDownScrubber == true) {
            var newX = e.clientX;
            // Get width of videoScrubberBox element
            var scrubHandle = document.getElementById('scrubHandle');
            var scrubHandleTringle = document.getElementById('scrubHandleTringle');
            var leftAlignElementBox = (document.getElementById('thD0')).getBoundingClientRect();
            var rightAlignElementBox = (document.getElementById('bottomTimelineControls')).getBoundingClientRect();
            var hlsVideoElements = document.getElementsByClassName('hlsContainer');
            var cameraTableTH = document.getElementById('cameraTableTH');
            var playButtonElement = document.getElementById('playButtonElement');

            for (var container of hlsVideoElements) {
                container.pause();
            }

            // Make CSS button pause
            var scrubberPercentage;
            // First, check if left side is visible or not
            if (leftSidePopped == true) {
                // 10%
                if (newX > (leftAlignElementBox.left) && newX < (rightAlignElementBox.right)) {
                    var calculatedX = ((newX - 255) + "px");

                    // Calculate to zero for percentage calcualtion
                    scrubHandleTringle.style.left = ((newX - 255) - 13) + "px"
                    scrubHandle.style.left = (calculatedX)
                    var scrubHandleZeroed = ((scrubHandle.style.left).replace('px', '') - (cameraTableTH.offsetWidth));
                    var scrubHandleTop = (rightAlignElementBox.right) - (cameraTableTH.offsetWidth + 255)
                    scrubberPercentage = (scrubHandleZeroed / scrubHandleTop) * 100;
                }
                else if (newX >= (rightAlignElementBox.right)) {
                    console.log("At End")
                    scrubHandleTringle.style.left = ((rightAlignElementBox.right - 273)) + "px"
                    scrubHandle.style.left = ((rightAlignElementBox.right - 273) + 15) + "px"
                    scrubberPercentage = 100;
                }
                else {
                    console.log("At Start")
                    scrubHandleTringle.style.left = ("calc(10% - 15px)")
                    scrubHandle.style.left = ("10%") 
                    scrubberPercentage = 0;
                }
            }
            else {
                // 10%
                if (newX > (leftAlignElementBox.left) && newX < (rightAlignElementBox.right)) {
                    var calculatedX = ((newX) + "px");
                    scrubHandleTringle.style.left = ((newX) - 13) + "px"
                    scrubHandle.style.left = (calculatedX)
                    var scrubHandleZeroed = ((scrubHandle.style.left).replace('px', '') - (cameraTableTH.offsetWidth));
                    var scrubHandleTop = (rightAlignElementBox.right) - (cameraTableTH.offsetWidth)
                    scrubberPercentage = (scrubHandleZeroed / scrubHandleTop) * 100;
                }
                else if (newX >= (rightAlignElementBox.right)) {
                    console.log("At End")
                    scrubHandleTringle.style.left = ((rightAlignElementBox.right - 23)) + "px"
                    scrubHandle.style.left = ((rightAlignElementBox.right - 23) + 15) + "px"
                    scrubberPercentage = 100;
                }
                else {
                    console.log("At Start")
                    scrubHandleTringle.style.left = ("calc(10% - 15px)")
                    scrubHandle.style.left = ("10%")
                    scrubberPercentage = 0;
                }
            }

            var syncTime = (hlsVideoElements[0].duration * scrubberPercentage) / 100;

            // End of calcs, apply to video
            for (var container of hlsVideoElements) {
                // container.play()
                // container.currentTime = (container.duration * scrubberPercentage) / 100;
                container.currentTime = syncTime
                // container.pause()
            }
        }
    });
    // EVENT LISTENER END

    

    // Time update event listenr function
    function timeUpdateListener(event) {
        // Take hlsVideoElements[0].currentTime and figure out pixel position based on that
        
        // Get percentage we can use
        var hlsVideoElements = document.getElementsByClassName('hlsContainer');
        var videoScrubberPercentage = (hlsVideoElements[0].currentTime / hlsVideoElements[0].duration)
        var mainBox = (document.getElementById('bottomTimelineControls')).getBoundingClientRect();
        var cameraTableTH = document.getElementById('cameraTableTH').getBoundingClientRect();
        var thD0 = document.getElementById('thD0').getBoundingClientRect();
        
        // Determine coordinates based on reverse
        // var pixelBottom = (mainBox.left);
        var pixelBottom = cameraTableTH.width
        // pixelBottom = pixelBottom + (cameraTableTH.width - thD0.width) // Offset

        var pixelTop = (mainBox.right - (255))
        // pixelTop = (pixelTop - (cameraTableTH.width - thD0.width)) // Offset
        // pixelTop = pixelTop  - 70
        
        
        var diff = pixelTop - pixelBottom;
        var diffXPercent = diff * videoScrubberPercentage
        var finalPixelCoord = (pixelBottom + diffXPercent) - 3
        
        scrubHandle.style.left = (finalPixelCoord + "px")
        scrubHandleTringle.style.left = ((finalPixelCoord - 13) + "px")
    }
}

export function submitQueryToServer() {
    // Loop over all elements with class 'selectCameraItem', put all that are checkbox true in array
    // Get From and To times from datetime elements
    // Submit POST request to server with data format as:
    // [[camera1, camera2], datefrom, dateto]
    var toSendArray = [];
    var camListArray = [];
    var allowToPost = true;
    var fromTimeDateObject = null;
    var toTimeDateObject = null;

    // Select all elements with class 'selectCameraItem'
    var allCheckboxCameras = document.getElementsByClassName('selectCameraItem');

    for (var checkBoxElement of allCheckboxCameras) {
        // For each checkboxDiv checkfor input element
        var inputElement = checkBoxElement.querySelector('input');

        if (inputElement.checked == true) {
            
            // Append label text content to camListArray
            var labelElement = checkBoxElement.querySelector('label');
            camListArray.push(labelElement.textContent);
        }
    }
    
    toSendArray.push(camListArray);
    
    // Check if any cameras are selected
    if (camListArray.length == 0) {
        alert("Please select at least 1 camera");
        allowToPost = false;
    }
    else if (camListArray.length > 6) {
        // Eventually fix to 9, anything above 6 gives CSS issues
        alert("Can only select 6 cameras, please reduce");
        allowToPost = false;
    }

    // Cameras selected, get from and to time and push to array
    // Get from time
    var fromTimeElement = document.getElementById('datetimefrom');

    // If value is none then break raise alert
    if (fromTimeElement.value.length == 0 && allowToPost == true) {
        alert("Need to set FROM time in Step 2")
        allowToPost = false;
    }
    else {
        fromTimeDateObject = new Date(fromTimeElement.value);
        toSendArray.push(fromTimeElement.value)
    }

    var toTimeElement = document.getElementById('datetimeto');

    // If value is none then break raise alert
    if (toTimeElement.value.length == 0 && allowToPost == true) {
        alert("Need to set TO time in Step 2")
        allowToPost = false;
    }
    else {
        toTimeDateObject = new Date(toTimeElement.value);
        toSendArray.push(toTimeElement.value)
    }

    // Check if TO time is after FROM time
    if (fromTimeDateObject > toTimeDateObject) {
        alert("FROM Time is After TO Time, please correct.")
        allowToPost = false;
    }
    // If FROM == TO
    if (fromTimeElement.value == toTimeElement.value) {
        alert("FROM Time is same as TO Time, please correct.")
        allowToPost = false;
    }


    // Only submit POST request if none of the info way blank
    if (allowToPost == true) {

        // Send POST Request to server for getting m3u8 file to stream from
        fetch('/search/m3u8request',
        {
            method: 'POST',
            headers: {
                'Content-Type': 'application/plain'
            },
            body: (JSON.stringify(toSendArray))
        }
        ).then(response => {
            const data = (response.text())
            .then(data => {                
                // data will contain m3u8 strings seperated by |, recreate into array
                var m3u8StringArray = data.split("|");

                // Hide bottom version banner for more space and set new element positions and heights
                var hideme = document.getElementsByClassName('bottom-bar');
                hideme[0].style.display = 'none';

                var leftSidePopup = document.getElementById('leftSidePopup');
                leftSidePopup.style.bottom = '0px';

                var bottomTimelineControls = document.getElementById('bottomTimelineControls');
                var step1selectcameras = document.getElementById('step1selectcameras');
                
                bottomTimelineControls.style.transform = 'translateY(631px)';
                bottomTimelineControls.style.height = '155px';
                step1selectcameras.style.height = 'calc(100vh -  502px)';

                // Call generateVideoTray
                generateVideoTray(m3u8StringArray, camListArray)

                // Regenerate Timeline
                generateTimelineEmpty(fromTimeElement.value, toTimeElement.value, camListArray);

                // Add motion events to the Timeline, assuming timeline is generated
        })})
    }
}

// Function run to register eventLister for playBackSpeedSelect change, then itterates over all hlsContainer objects and sets playback speed
function playBackSpeedListener() {

    // Set initial grey out, changes when videos are requested

    var playBackSpeedSelectElement = document.getElementById('playBackSpeedSelect');

    playBackSpeedSelectElement.style.opacity = '0.5';
    playBackSpeedSelectElement.style.pointerEvents = 'none';

    
    playBackSpeedSelectElement.addEventListener('change', (e) => {
        var hlsVideoElements = document.getElementsByClassName('hlsContainer');
        // Has changed value, get new value and apply to all videos
    
        var newPlayBackSpeed = Number((playBackSpeedSelectElement.value).replace('x', ''))

        // Apply to all videos
        for (var container of hlsVideoElements){
            container.playbackRate = newPlayBackSpeed;
        }
    });


}

async function onFinishedLoading() {
    // Parse window.localcameras
    window.localcameras = window.localcameras.replace(/&#39;/g, '');
    // Split into array by |
    window.localcameras = localcameras.split("|");

    // Add to Camera list over loop
    for (var camera of window.localcameras) {
        addCameraItemDiv(camera);
    }

    // Set current time and date to both datetime-local elements, one hour difference
    var fromTimeElement = document.getElementById('datetimefrom');
    var toTimeElement = document.getElementById('datetimeto');

    // Current bug where if past midnight until 1am fromDate is not set
    // Get current datetime
    var currentDateTime = new Date()
    // Conversions
    var formattedLocalTimeDate = currentDateTime.getFullYear() + '-' +
                        ('0' + (currentDateTime.getMonth() +  1)).slice(-2) + '-' +
                        ('0' + currentDateTime.getDate()).slice(-2) + 'T' +
                        ('0' + currentDateTime.getHours()).slice(-2) + ':' +
                        ('0' + currentDateTime.getMinutes()).slice(-2);
    // Set toTimeValue
    toTimeElement.value = formattedLocalTimeDate;
    
    var formattedLocalTimeDateMinusOneHour = currentDateTime.getFullYear() + '-' +
                        ('0' + (currentDateTime.getMonth() +  1)).slice(-2) + '-' +
                        ('0' + currentDateTime.getDate()).slice(-2) + 'T' +
                        ('0' + (currentDateTime.getHours() - 1)).slice(-2) + ':' +
                        ('0' + currentDateTime.getMinutes()).slice(-2);

    // Set fromTimeValue
    fromTimeElement.value = formattedLocalTimeDateMinusOneHour;

    // Register playback dropdown element change
    playBackSpeedListener();

    // Add event listener to collapseButton
    var collapseButtonElement = document.getElementById('collapseButton');
    collapseButtonElement.addEventListener('click', () => {
        // Check if side is out or in
        
        var leftSide = document.getElementById('leftSidePopup');
        var videoContainer = document.getElementById('videoContainer');
        var bottomTimelineControls = document.getElementById('bottomTimelineControls');
        var leftSideCollapseButton = document.getElementById('leftSideCollapseButton');
        var collapseButton = document.getElementById('collapseButton');
        leftSideCollapseButton.style.position = 'absolute';
        leftSideCollapseButton.style.top = '45px';

        if (leftSidePopped == true) {
            // Hide 
            leftSide.style.display = 'none';
            videoContainer.style.left = '0px';
            bottomTimelineControls.style.left = '0px';
            bottomTimelineControls.style.width = 'calc(100vw - (325px - 255px))';
            leftSideCollapseButton.style.left = '0px';
            collapseButton.style.transform = '';

            leftSidePopped = false;

        }
        else {
            leftSide.style.display = 'block';
            videoContainer.style.left = '250px';
            bottomTimelineControls.style.left = '255px';
            bottomTimelineControls.style.width = 'calc(100vw - (325px))';
            leftSideCollapseButton.style.left = '250px';
            collapseButton.style.transform = 'scaleX(-1)';
            leftSidePopped = true;
        }
        // Regenerate playback head position!
        // TODO
    });

    // Set button to be flipped normally
    var collapseButton = document.getElementById('collapseButton');
    collapseButton.style.transform = 'scaleX(-1)';

    // Download loading gif
    var requestGif = await fetch('/static/loading_wheel-white.gif');
    var requestGifData = await requestGif.blob();
    srvUrl = URL.createObjectURL(requestGifData)

}

window.onload = onFinishedLoading();