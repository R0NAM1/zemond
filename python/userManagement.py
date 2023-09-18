import cryptocode
from globalFunctions import passwordRandomKey, myCursor, myDatabase, sendONVIFRequest

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

