# Permission tree will be a JSON object for simplicity.
permissionTreeObject = {
    
    "permissionRoot": {
        
        "dashboard": {
            "test": {
                "myface": {}
            }
            },
        
        "monitors": {},
        
        "camera_list": {
            "view_camera": {}
            },
        
        "search": {},
        
        "settings": {
            "add_user": {},
            "reset_password": {},
            "sync_ldap": {},
            "delete_user": {},
            "add_camera": {},
            "camera_models": {},
            "add_camera_manual": {},
            "delete_camera": {}
        },
        
        "userSettings": {
          "accountActive": {},
          "suspendedLogin": {},
          "u2fkeyenabled": {}  
            
        }
    }
    
}