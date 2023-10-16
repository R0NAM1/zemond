import psycopg2
import globalFunctions

# Needed Before Running: A Postgres DB server with a DB called 'zemond', and a user with all privileges called 'zemond'.

databaseURL = globalFunctions.databaseURL
databasePort = globalFunctions.databasePort
databaseUser = globalFunctions.databaseUser
databaseName = globalFunctions.databaseName
databaseUserPassword = globalFunctions.databaseUserPassword

# In this file we enter an empty database and prepare all the existing tables with headers and such.
# First We Add Our Tables, subnets, localcameras, cameradb, cameraEvents, credentials.
# This will change as time goes on

myDatabase = psycopg2.connect(database=databaseName,
                        host=databaseURL,
                        user=databaseUser,
                        password=databaseUserPassword,
                        port=databasePort)

cursor = myDatabase.cursor()

print("Making subnet Table Now")

# Create Table subnets With Data
cursor.execute("""CREATE TABLE IF NOT EXISTS subnets (
   subnetScope VARCHAR(15) UNIQUE,
   subnetName VARCHAR(50) UNIQUE
);""")

print("Making localcameras Table Now")

# Create Table localcameras With Data
# 'model' is the link we use to our cameradb table, which holds manufacturing info.
cursor.execute("""CREATE TABLE IF NOT EXISTS localcameras (
   name VARCHAR(50) UNIQUE,
   onvifURL VARCHAR(500),
   rtspURL VARCHAR(500),
   username VARCHAR(500),
   password VARCHAR(5000),
   credgroup VARCHAR(500),
   manufacturer VARCHAR(500) ,
   model VARCHAR(500),
   serialnumber VARCHAR(500) UNIQUE,
   firmwareversion VARCHAR(500),
   dockerIP VARCHAR(500)
);""")

print("Making cameradb Table Now")

# Create Table cameradb With Data
cursor.execute("""CREATE TABLE IF NOT EXISTS cameradb (
   model VARCHAR(50) UNIQUE,
   manufacturer VARCHAR(50) ,
   hasptz BOOLEAN NOT NULL,
   hasTWA BOOLEAN NOT NULL,
   image VARCHAR );""")

print("Making cameraEvents Table Now")

# Create Table cameraEvents With Data
cursor.execute("""CREATE TABLE IF NOT EXISTS cameraEvents (
   name VARCHAR(5000),
   topic VARCHAR(5000),
   messagetime TIMESTAMP,
   data JSONB
)""") #datastring formatted as name:value

print("Making credentials Table Now")

# Create User Table
cursor.execute("""CREATE TABLE IF NOT EXISTS userTable (
   username VARCHAR(50),
   password VARCHAR(5000),
   permissions VARCHAR[],
   camPermissions VARCHAR[]);""")

cursor.execute("""CREATE TABLE IF NOT EXISTS auditLog (
   timeLogged TIMESTAMP,
   username VARCHAR(50),
   auditLogLevel varchar(50),
   auditMessage varchar (500)
   );""")

cursor.execute("""CREATE TABLE IF NOT EXISTS configuredMonitors (
   camArray JSONB,
   timeInfo varchar(50) DEFAULT '0s',
   monitorName varchar(50),
   monitorTemplate varchar (500),
   attMap varchar(50),
   lengthbywidthnum varchar(3)
   );""")
# Commit Changes To Database
myDatabase.commit()

# Database is now preconfigured!