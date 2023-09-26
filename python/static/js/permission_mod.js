function generateOptions(jsonTree, prefix = '', options = []) {
    // JSONTREE is the base tree, prefix always updates to the newpath (Down line in tree),
    // options is the current logged string branches.
    // For every following key in my tree
    for (let key in jsonTree) {
        // Set newpath to my existing prefix and add the latest key, if at the root (No Prefix), just add the next keys
        let newPath = prefix ? (prefix + '.' + key) : key;
        // Push newPath (Branch string) to the options Array
        options.push(newPath)

        // If our key IS an object and it has a length, then recursively run this until we run out of tree to climb.
        if (typeof jsonTree[key] == 'object' && Object.keys(jsonTree[key]).length > 0) {
            generateOptions(jsonTree[key], newPath, options);
        }
    }

    return options;
}

function createSelect(treeStart) {

    const finalTreeArray = [];


    processedTree = (window.permissionTreeObject).replace(/&#39;/g, '"')
    // console.log(processedTree)
    jsonTree = JSON.parse(processedTree)
    // console.log(jsonTree)
    // Generate multiple strings to represent tree based permission objects, itterate into a select element.
    permissionOptions = generateOptions(jsonTree)
    // console.log(permissionOptions)
    for (let permission of permissionOptions) {
        
        const elementOption = document.createElement('option')
        elementOption.value = permission;
        elementOption.text = permission;
        treeStart.appendChild(elementOption)
    }
    


}

function addPerm(username) {
    // Grab Permission Selected
    const feedbackDiv = document.getElementById('feedbackMsg');
    while (feedbackDiv.firstChild) {
        feedbackDiv.removeChild(feedbackDiv.firstChild)
    }
    const permTreeElement = document.getElementById('permissionsTree');
    for (let i = permTreeElement.children.length - 1; i >= 0; i--) {
        let child = permTreeElement.children[i];
        if (child.tagName === 'SELECT') {

            let reqPerm = child.value;
            // Wildcard check
            let wildBox = document.getElementById('wildBox');
            if (wildBox.checked) {
                reqPerm = reqPerm + '.*';
            }

            fetch('/settings/manage_perms',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/plain'
                },
                body: ("addPerm:" + reqPerm + ":" + username)
            }
            ).then(response => {
                const data = (response.text())
                .then(data => {
                    if (data == 'TRUE') {
                        // User was assigned permisson, reload.
                        loadUserPermissions(userselect.value)
                    }
                    else {
                        // User already had permission, inform client.
                        const feedbackMsg = document.createElement('h3')
                        feedbackMsg.textContent = 'User already has permission.'
                        feedbackDiv.appendChild(feedbackMsg);
                    }
                })})
                    
                }
    }}

function rmPerm(username) {
    const feedbackDiv = document.getElementById('feedbackMsg');
    while (feedbackDiv.firstChild) {
        feedbackDiv.removeChild(feedbackDiv.firstChild)
    }

    // If select element exists
    const assignedPermissions = document.getElementById('assignedPermissions');
    for (let i = assignedPermissions.children.length - 1; i >= 0; i--) {
        let child = assignedPermissions.children[i];
        if (child.tagName === 'SELECT') {

            // Send request to delete, usually should return yes.

            fetch('/settings/manage_perms',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/plain'
                },
                body: ("rmPerm:" + child.value + ":" + username)
            }
            ).then(response => {
                const data = (response.text())
                .then(data => {
                    if (data == 'TRUE') {
                        // User permission removed, reload
                        loadUserPermissions(userselect.value)
                    }
                    else {
                        // Something is terribly wrong.
                        const feedbackMsg = document.createElement('h3')
                        feedbackMsg.textContent = 'Got a FALSE, something went very wrong.'
                        feedbackDiv.appendChild(feedbackMsg);
                    }
                })})

        }}
    }
function addCam(username) {
    const feedbackDiv = document.getElementById('feedbackMsg');
    while (feedbackDiv.firstChild) {
        feedbackDiv.removeChild(feedbackDiv.firstChild)
    }

    // If select element exists
    const cameraList = document.getElementById('cameraList');
    for (let i = cameraList.children.length - 1; i >= 0; i--) {
        let child = cameraList.children[i];
        if (child.tagName === 'SELECT') {
    
       // Send request to delete, usually should return yes.

       fetch('/settings/manage_perms',
       {
           method: 'POST',
           headers: {
               'Content-Type': 'application/plain'
           },
           body: ("addCam:" + child.value + ":" + username)
       }
       ).then(response => {
           const data = (response.text())
           .then(data => {
               if (data == 'TRUE') {
                   // Camera added, reload
                   loadUserPermissions(userselect.value)
               }
               else {
                //    Already has camera
                   const feedbackMsg = document.createElement('h3')
                   feedbackMsg.textContent = 'Camera Already Assigned.'
                   feedbackDiv.appendChild(feedbackMsg);
               }
           })})      

        }
    }}

function rmCam(username) {
    const feedbackDiv = document.getElementById('feedbackMsg');
    while (feedbackDiv.firstChild) {
        feedbackDiv.removeChild(feedbackDiv.firstChild)
    }

    // If select element exists
    const assignedCams = document.getElementById('assignedCams');
    for (let i = assignedCams.children.length - 1; i >= 0; i--) {
        let child = assignedCams.children[i];
        if (child.tagName === 'SELECT') {

            // Send request to delete, usually should return yes.

            fetch('/settings/manage_perms',
            {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/plain'
                },
                body: ("rmCam:" + child.value + ":" + username)
            }
            ).then(response => {
                const data = (response.text())
                .then(data => {
                    if (data == 'TRUE') {
                        // User permission removed, reload
                        loadUserPermissions(userselect.value)
                    }
                    else {
                        // Something is terribly wrong.
                        const feedbackMsg = document.createElement('h3')
                        feedbackMsg.textContent = 'Got a FALSE, something went very wrong.'
                        feedbackDiv.appendChild(feedbackMsg);
                    }
                })})

        }}
}

function loadUserPermissions(username) {
    // Send post request to server using fetch meathod
    fetch('/settings/manage_perms',
    {
        method: 'POST',
        headers: {
            'Content-Type': 'application/plain'
        },
        body: ("getPermissions:" + username)
    }
    ).then(response => {
        const data = (response.text())
        .then(data => {
            const modData = data.substring(3, data.length - 3);
            // console.log(modData)
            const slicedArrary = modData.split("], [");
            let permissions = slicedArrary[0].replaceAll("'", "");
            permissions = permissions.split(", ")
            let camperms = slicedArrary[1]
            camperms = camperms.replaceAll("'", "");
            camperms = camperms.split(', ')

            // Cleanup IF exists
            const permTreeElement = document.getElementById('permissionsTree');
            const localCameraLists = document.getElementById('cameraList');
            const assignedPermElement = document.getElementById('assignedPermissions');
            const userCamList = document.getElementById('assignedCams');
            let wildBox = document.getElementById('wildBox');
            wildBox.checked = false;

            for (let i = permTreeElement.children.length - 1; i >= 0; i--) {
                let child = permTreeElement.children[i];
                if (child.tagName === 'SELECT') {
                    permTreeElement.removeChild(child);
                }
            }

            for (let i = localCameraLists.children.length - 1; i >= 0; i--) {
                let child = localCameraLists.children[i];
                if (child.tagName === 'SELECT') {
                    localCameraLists.removeChild(child);
                }
            }

            for (let i = assignedPermElement.children.length - 1; i >= 0; i--) {
                let child = assignedPermElement.children[i];
                if (child.tagName === 'SELECT') {
                    assignedPermElement.removeChild(child);
                }
            }

            for (let i = userCamList.children.length - 1; i >= 0; i--) {
                let child = userCamList.children[i];
                if (child.tagName === 'SELECT') {
                    userCamList.removeChild(child);
                }
            }
    
            const treeStart = document.createElement('select');
            permTreeElement.appendChild(treeStart)

            // console.log(window.cameraList)

            // Load Cameras
            if ((window.cameraList).includes('&#39;')) {
                cameraList = (window.cameraList).replace(/&#39;/g, '');
                cameraList = cameraList.substring(1, cameraList.length - 1)
                cameraList = cameraList.split(", ")
                // Clean each array entry of () and ,
                for (let i = 0; i < cameraList.length; i++) {
                    cameraList[i] = cameraList[i].substring(1, cameraList[i].length - 2);
                }
            }

            // Generate base permission tree
            createSelect(treeStart)

            const selectCamElement = document.createElement('select');
            localCameraLists.appendChild(selectCamElement)

            for (let camera of cameraList) {
                const camOption = document.createElement('option')
                camOption.value = camera;
                camOption.text = camera;
                selectCamElement.appendChild(camOption)
            }



            // Create given permissions
            // Take these two and load them into DOM elements, 
            // Load assigned permissions
            const selectElement = document.createElement('select');
            assignedPermElement.appendChild(selectElement);

            for (let permission of permissions ) {
                const elementOption = document.createElement('option')
                elementOption.value = permission;
                elementOption.text = permission;
                selectElement.appendChild(elementOption)
            }

            // Load Assigned Cameras
            const userSelectElement = document.createElement('select');
            userCamList.appendChild(userSelectElement)

            for (let camera of camperms) {
                const ucamOption = document.createElement('option')
                ucamOption.value = camera;
                ucamOption.text = camera;
                userSelectElement.appendChild(ucamOption)
            }
        })
    })
}