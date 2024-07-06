import cryptocode, json, traceback
from globalFunctions import passwordRandomKey, myCursor, myDatabase, sendONVIFRequest, doDatabaseQuery
from permissionTree import permissionTreeObject
from datetime import datetime, timezone

# In this file, we will have createUser(username, password), verifyUserAndPassword(), getUserDetails(), importLDAPUsersFr

# We have username, password, i know I eventually want object permissons, like if flag cam see cam camname, but will implement with audit logs later

def createUser(username, password):
    #Take username, encrypt password and insert into database
    # Check if entry exists    
    myCursor.execute("Select * from userTable WHERE username='{0}'".format(username))
    isUsername = myCursor.fetchone()
    if isUsername is None:
        passwordEncrypted = cryptocode.encrypt(password, passwordRandomKey)
        myCursor.execute("INSERT INTO userTable (username, password) VALUES(%s, %s)", (username, passwordEncrypted))
        myDatabase.commit()
        return True
    else:
        return False
        
# Verify user entry exists
def verifyDbUser(username):
    userExists = False
    myCursor.execute("Select username from userTable;")
    userTableTuple = myCursor.fetchall()
    # Itterate through tupple, see if exists
    for iusername in userTableTuple:
        if username in iusername:
            userExists = True
        else:
            userExists = False
    return True
    
# Encrypt new password pass into database.
def resetUserPass(username, password):
    passwordEncrypted = cryptocode.encrypt(password, passwordRandomKey)
    myCursor.execute("UPDATE userTable SET password=(%s) WHERE username = '{0}'".format(username), (passwordEncrypted, ))
    myDatabase.commit()
    
# Pass through user and password, return true if user exists and password matches
def verifyUserPassword(username, password):
    isUser = verifyDbUser(username)
    if isUser == True:
        myCursor.execute("Select password from userTable WHERE username='{0}'".format(username))
        dbPassword = myCursor.fetchone()
        if (password == cryptocode.decrypt(str(dbPassword), passwordRandomKey)):
            return True
        else:
            return False
        
# Delete selected user from db
def deleteUser(username):
    isUser = verifyDbUser(username)
    if isUser == True:
        myCursor.execute("DELETE FROM userTable WHERE username='{0}'".format(username))
        myDatabase.commit()
        
def cameraPermission(username, camString):
    try:
        myCursor.execute("Select camPermissions from userTable WHERE username='{0}'".format(username))
        camPerms = myCursor.fetchall()
        for perm in camPerms[0][0]:
            # If we grabbed that perm from the database, show here:
            if camString == perm:
                return True
        sendAuditLog(username, "MEDUIM", "Camera permission denied, needs '" + camString + "' permission")
        return False
    except Exception as e:
        print('Exception in checking camera permission, follows: ' + str(e))
        pass

def auditUser(username, permissionString):
    permExist = False
    
    # Check if permission exists:
    permissionTree = permissionTreeObject
    
    segements = permissionString.split('.')
    
    # Check if permission passed is in the tree
    for segement in segements:
        if segement in permissionTree:
            permissionTree = permissionTree[segement]
            permExist = True
        else:
            permExist = False
            break
    # If not a misspelling, check if user had permission
    if permExist == True:
        while True:
            try:
            # Call user database check if has permission
                # myCursor.execute("Select permissions from userTable WHERE username='{0}'".format(username))
                # userPermissions = myCursor.fetchall()
                userPermissions = doDatabaseQuery("Select permissions from userTable WHERE username='{0}'".format(username))
                userPermissionsProcessed = userPermissions[0]
            # If any of the users permissions match the inputted one, allow.
                for permission in userPermissionsProcessed[0]:
                    # print(permission)
                    # print(permissionString)
                    if permission == permissionString:
                        return True
                    
                    # IF the permission has a wildcard, trim back and check
                    elif '*' in permission:
                        permissionTree = permissionTreeObject
                        # If wildcard, check how far it goes:
                        permissionsplit = permission.split('.')                    
                        for segement in permissionsplit:
                            # Check to see if it follows the tree structure
                            if segement in permissionTree:
                                permissionTree = permissionTree[segement]
                                # Keep going until the segment is a wildcard, then match
                            elif segement == '*':
                                # If the final segment is a wildcard then we need the trim back the wildcard by 1,
                                # then we have the length we want our permissionString to be so we can compare them, and if they are the same,
                                # grant access!
                                # Trim wildcard and get wanted length
                                splitWildcardPermission = permission.split('.')[:-1]
                                requiredLength = len(splitWildcardPermission)
                            
                                # Split the permission string and trim it back to the wanted length by the difference
                                splitPermissionString = permissionString.split('.')
                                splitPermissionStringLength = len(splitPermissionString)
                                trimDiff = abs(requiredLength - splitPermissionStringLength)
                                trimmedPermissionString = splitPermissionString[:-trimDiff]
                                
                                # Reassemble strings and compare
                                joinString = '.'
                                reassem_wildcard = joinString.join(splitWildcardPermission)
                                reassem_permissionString = joinString.join(trimmedPermissionString)
                                
                                # print("Your input trimmed: " + str(reassem_permissionString))
                                # print("The wildcard we are checking against: " + str(reassem_wildcard))
                                # print("The Trim Back Amount: " + str(trimDiff))
                                if (reassem_wildcard == reassem_permissionString):
                                    return True

                            elif len(permissionTree != 0):
                                return False
                
                # If not send to audit log
            except Exception as e:
                print("Exception in Permission Check, follows: " + str(e))
                tb = traceback.format_exc()
                print("Traceback: " + str(tb))
                pass
            # Only audit if permission is real and user does not have it
            sendAuditLog(username, "LOW", "Permission denied, needs '" + permissionString + "' permission")
            return False
    
    
def sendAuditLog(username, loglevel, logmessage):
    # Loglevel is TINY, LOW, MEDUIM, HIGH, SEVERE
    myCursor.execute("INSERT INTO auditLog (timeLogged, username, auditLogLevel, auditMessage) VALUES (%s, %s, %s, %s);", (datetime.now(timezone.utc), username, loglevel, logmessage))
    myDatabase.commit()