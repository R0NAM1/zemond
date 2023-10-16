function xbxedit(monname) {
    console.log(monNewName.value)
    if (monNewName.value){
        location.href = ('/monitors/xbxedit/' + monname)
    }
    else if (monNewName.value == '') {
        
    }
}


function openTab(tabId) {
    var existTab = document.getElementById("existTab");
    var newTab = document.getElementById("newTab");

    if (tabId == "existTabContent") {
        existTab.style.backgroundColor = "darkgrey";
        newTab.style.backgroundColor = "lightgrey";
    }
    else if (tabId == "newTabContent") {
        newTab.style.backgroundColor = "darkgrey";
        existTab.style.backgroundColor = "lightgrey";
    }

    // Hide all tab contents
    var tabContents = document.getElementsByClassName("tab-content");
    for (var i = 0; i < tabContents.length; i++) {
      tabContents[i].classList.remove("show");
    }
  
    // Show the selected tab content
    var selectedTabContent = document.getElementById(tabId);
    selectedTabContent.classList.add("show");
    
}