var mouseDownScrubber = false;
var playOrPause = 'play';
var timelineGenerated = false;

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
export function generateVideoTray(m3u8VideoObjects) {   
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
    
    if (m3u8VideoObjects.length <= 2) {
        gridColumns = m3u8VideoObjects.length;
        gridRows = 1;
    } 
    else {
        gridColumns = Math.ceil(Math.sqrt(m3u8VideoObjects.length))
        gridRows = Math.ceil(m3u8VideoObjects.length / gridColumns)
    }

    videoContainer.style.gridTemplateColumns = (`repeat(${gridColumns}, 1fr)`);
    videoContainer.style.gridTemplateRows = (`repeat(${gridRows}, 1fr)`);

    // For length of array, add amount of video containers with class hlsContainer
    var m3u8Index = 0;
    for (var m3u8String of m3u8VideoObjects) {
        
        // Generate video element 
        var thisVideoElement = document.createElement('video')
        
        // Set options
        // Change to false when scrubber is done
        thisVideoElement.contains = true;

        // Mute
        thisVideoElement.muted = true;

        // Set CSS options
        // thisVideoElement.style.position = 'absolute';
        thisVideoElement.style.height = 'auto';
        thisVideoElement.style.width = '100%';
        // thisVideoElement.style.transform = 'translate(-125px, 0)'       
        thisVideoElement.style.objectFit = 'contain';

        // If m3u8VideoObjects.length is 1, then change specific CSS,
        if (m3u8VideoObjects.length == 1) {
            thisVideoElement.style.height = '100%';
            thisVideoElement.style.width = '100%';
        } 

        // Set class
        thisVideoElement.className = 'hlsContainer';

        // Add video to container
        videoContainer.appendChild(thisVideoElement);

        // Edit m3u8 string to include server URL
        var loc = window.location;
        var hostFullName = (loc.protocol + '//' + loc.hostname + ':' + loc.port)
        m3u8String = m3u8String.replaceAll("/search/", hostFullName + "/search/")
        
        // Attatch m3u8String as hls
        var m3u8FileBlob = new Blob([m3u8String], {type: 'application/x-mpegURL'});
        // Url for blob that video element can use
        var m3u8InternalUrl = URL.createObjectURL(m3u8FileBlob);

        // //Check if HLS is supported, if so attatch
        if (Hls.isSupported()) {
            // console.log("Loading HLS")
            var hls = new Hls();
            // console.log("Loading Source")
            hls.loadSource(m3u8InternalUrl);
            // console.log("Attatching HLS")
            hls.attachMedia(thisVideoElement);
        }

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

export function generateTimelineEmpty(fromDate, toDate){
    // Generate scrubber timeline to syncronize all hlsContainer class video objects
    // This MUST be run before motion event data is requested since elements won't exist

    var scrubberContainer = document.getElementById('videoScrubberBox');
    var videoScrubberTriangle = document.getElementById('videoScrubberTriangle');

    // Enable videoScrubberTriangle
    videoScrubberTriangle.style.display = 'block';

    // Register event handlers to handle the scrubber setting time on videos
    // If mousedown on videoScrubber, then we can move it
    videoScrubberTriangle.addEventListener('mousedown', (e) => {
        e.preventDefault();
        // Set mouseDownScrubber to true
        mouseDownScrubber = true;
    });

    // If mouseup, we are for sure not mouse down on scrubber
    document.addEventListener('mouseup', (e) => {
        // Set mouseDownScrubber to false
        mouseDownScrubber = false;
    });

    // Grab all video elements
    var hlsVideoElements = document.getElementsByClassName('hlsContainer');
    var videoScrubberBoxElement = document.getElementById('videoScrubberBox');

    // By default set at minumim
    videoScrubberTriangle.style.left = ('-15' + 'px');
    
    // Event listen on mousemove to check if mouseDownScrubber is true, if so we can move in the bounding boxes
    document.addEventListener('mousemove', (e) => {
        if (mouseDownScrubber == true) {
            var newX = e.clientX;
            var calculatedX = (newX - 26 - 350);
            console.log("Calc X: " + calculatedX)
            // Get width of videoScrubberBox element
            
            if (calculatedX >= -15 && calculatedX <= (videoScrubberBoxElement.offsetWidth - 25)) {
                videoScrubberTriangle.style.left = (calculatedX + 'px');
            }
            else {

                if (calculatedX > 0) {
                    videoScrubberTriangle.style.left = ((videoScrubberBoxElement.offsetWidth - (25 + 5)) + 'px');
                }
                else {
                    videoScrubberTriangle.style.left = ('-15' + 'px');
                }
            }

            
            
            var absolutePosScrubber = (videoScrubberTriangle.style.left).replace('px', '')
            
            // Calculate percentage of where scrubber is, 
            var scrubberPercentage = ((absolutePosScrubber + 15) / videoScrubberBoxElement.offsetWidth) + 1;

            console.log("Scrubber X: " + (Number(absolutePosScrubber) + 15))
            console.log("Acul Width: " + videoScrubberBoxElement.offsetWidth)
            console.log("Scrubber %: " + scrubberPercentage)

            // Based on percentage, if equal or below 0, set timestamp to 0
            // If at or above 99, set last int in timestamp,
            // If inbetween, do math to calculate timestamp and apply

            
            // Timestamp checks
            // 0, At start check
            if (scrubberPercentage < 0) {
                for (var container of hlsVideoElements) {
                    container.currentTime = 0;
                }
            }
            // 99, At end check
            else if (scrubberPercentage > 99) {
                for (var container of hlsVideoElements) {
                    container.currentTime = container.duration;
                }
            }
            // Else check, for anything inbetween
            else {
                for (var container of hlsVideoElements) {
                    container.currentTime = (container.duration * scrubberPercentage) / 100;
                } 
            }

        }
    });
    // EVENT LISTENER END

    // Create play / pause button
    var playButtonElement = document.createElement('img');
    playButtonElement.style.width = "50px";
    playButtonElement.src = "/static/playButton.png";
    playButtonElement.style.left = '2px';
    playButtonElement.style.position = 'absolute';
    playButtonElement.style.cursor = 'pointer';
    playButtonElement.style.transform = 'translate(0, -2px)';
    

    // Time update event listenr function
    function timeUpdateListener(event) {
        // Take hlsVideoElements[0].currentTime and figure out pixel position based on that
        
        // Get percentage we can use
        var videoScrubberPercentage = (hlsVideoElements[0].currentTime / hlsVideoElements[0].duration)
        
        // Calculate pixel position from percentage
        var pixelPositon = (videoScrubberBoxElement.offsetWidth * videoScrubberPercentage) - 25;
        
        console.log("New Pixel Pos: " + pixelPositon)
        videoScrubberTriangle.style.left = (pixelPositon + 'px')
    }

    // Add event listen to listen for click, if so then press play on all video elements and based on first video in index, move custom scrubber
    playButtonElement.addEventListener('click', (e) => { 
        
        if (playOrPause == 'play') {

            // Loop over each video, pause each
            for (var container of hlsVideoElements) {
                container.play();
            }

            
            playButtonElement.src = "/static/pauseButton.png";
            playOrPause = 'pause'
            
            // Add event listener to update current scrubber
            hlsVideoElements[0].addEventListener('timeupdate', timeUpdateListener);
        }
        else if (playOrPause == 'pause') {

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

    // Append to div
    var playPauseButtonDiv = document.getElementById('playPauseButton');
    playPauseButtonDiv.appendChild(playButtonElement)

    // Create export button
    var exportButtonElement = document.getElementById('exportButton');
    var exportButtonElementImage = document.createElement('img');    
    exportButtonElementImage.style.width = "50px";
    exportButtonElementImage.src = "/static/exportButton.png";
    exportButtonElementImage.style.left = '2px';
    exportButtonElementImage.style.position = 'absolute';
    exportButtonElementImage.style.cursor = 'pointer';

    exportButtonElement.appendChild(exportButtonElementImage);
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
            var labelElement = checkBoxElement.querySelector('label');
            // Append label text content to camListArray
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

                // Call generateVideoTray
                generateVideoTray(m3u8StringArray)

                if (timelineGenerated == false) {
                // Generate Timeline if not already
                generateTimelineEmpty(fromTimeElement.value, toTimeElement.value);
                timelineGenerated = true;
                }

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

function onFinishedLoading() {
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

    playBackSpeedListener();
}

window.onload = onFinishedLoading();