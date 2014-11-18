'''
@author Gonzalo Gasca Meza
		AT&T Labs 
		Date: November 2014
		Purpose: Emulates TelePresence Server 8710 Server API
'''

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from threading import Thread
from multiprocessing import Process
from os import urandom
from random import randrange
from itertools import islice, imap, repeat
from types import *
from urlparse import urlparse
from random import randint
import time, string, csv, threading, logging, copy, re

# TODO: Add configuration file for settings via import
# TODO: Refactoring
# TODO: Add SIP stack


# #########################################################################
hostname = "127.0.0.1"
port = 8080
version = '4.0(1.57)'
systemUserName = "sutapi"
systemPassWord = "pwd22ATS!"
systemConfigurationFile = 'conf/system.xml'
systemConferenceList = 'conf/conference.conf'
systemParticipantList = 'conf/participants.conf'
systemMode = -1
activeCalls = []
activeCallsInFile = []
feedBackServerList = {}
feedbackReceiverIndex = []


# Configuration parameters
configParameters = [
    'portsContentFree',
    'locked',
    'oneTableMode',
    'portsAudioFree',
    'roundTableEnable',
    'videoPortLimit',
    'conferenceID',
    'persistent',
    'portsVideoFree',
    'audioPortLimit',
    'conferenceGUID',
    'audioPortLimitSet',
    'pin',
    'active',
    'videoPortLimitSet',
    'registerWithGatekeeper',
    'numericID',
    'participantList',
    'recording',
    'registerWithSipRegistrar',
    'h239ContributionID',
    'conferenceName',
    'tsURI',
    'useLobbyScreen',
    'lobbyMessage',
    'useWarning',
    'lockDuration',
    'duration']

# Conference parameters
conferenceParameters = {
    0: 'portsContentFree',
    1: 'locked',
    2: 'oneTableMode',
    3: 'portsAudioFree',
    4: 'roundTableEnable',
    5: 'videoPortLimit',
    6: 'conferenceID',
    7: 'persistent',
    8: 'portsVideoFree',
    9: 'audioPortLimit',
    10: 'conferenceGUID',
    11: 'audioPortLimitSet',
    12: 'pin',
    13: 'active',
    14: 'videoPortLimitSet',
    15: 'registerWithGatekeeper',
    16: 'numericID',
    17: 'participantList',
    18: 'recording',
    19: 'registerWithSipRegistrar',
    20: 'h239ContributionID',
    21: 'conferenceName',
    22: 'tsURI',
    23: 'useLobbyScreen',
    24: 'lobbyMessage',
    25: 'useWarning',
    26: 'lockDuration',
    27: 'duration'
}

#System Errors
systemErrors = {
    1: 'Method not supported',
    2: 'Duplicate conference name',
    4: 'No such conference or auto attendant',
    5: 'No such participant',
    6: 'Too many conferences.',
    8: 'No conference name or auto attendant id supplied',
    10: 'No participant address supplied',
    13: 'Invalid PIN specified',
    15: 'Insufficient privileges',
    16: 'Invalid enumerateID value',
    17: 'Port reservation failure',
    18: 'Duplicate numeric ID',
    20: 'Unsupported participant type',
    25: 'New port limit lower than currently active',
    34: 'Internal error',
    35: 'String is too long',
    101: 'Missing parameter',
    102: 'Invalid parameter',
    103: 'Malformed parameter',
    105: 'Request too large',
    201: 'Operation failed',
    202: 'Product needs its activation feature key',
    203: 'Too many asynchronous requests'
}

#Data Type
conferenceFieldDataType = [
    IntType,  # 0  - portsContentFree
    BooleanType,  # 1  - locked
    IntType,  # 2  - oneTableMode
    IntType,  # 3  - portsAudioFree
    BooleanType,  # 4  - roundTableEnable
    IntType,  # 5  - videoPortLimit
    IntType,  # 6  - conferenceID
    BooleanType,  # 7  - persistent
    IntType,  # 8  - portsVideoFree
    IntType,  # 9  - audioPortLimit
    StringType,  # 10 - conferenceGUID
    BooleanType,  # 11 - audioPortLimitSet
    IntType,  # 12 - pin
    BooleanType,  # 13 - active
    BooleanType,  # 14 - videoPortLimitSet
    BooleanType,  # 15 - registerWithGatekeeper
    IntType,  # 16 - numericID
    ListType,  # 17 - participantList
    BooleanType,  # 18 - recording
    BooleanType,  # 19 - registerWithSipRegiStringTypear
    IntType,  # 20 - h239ContributionID
    StringType,  # 21 - conferenceName
    StringType,  # 22 - tsURI
    BooleanType,  # 23 - useLobbyScreen
    StringType,  # 24 - lobbyMessage
    BooleanType,  # 25 - useWarning
    IntType,  # 26 - lockDuration
    IntType,  # 27 - duration
]

#Data Type for Participant
participantFieldDataType = [
    StringType,  # 0  - participantId
    BooleanType, # 1
    StringType,  # 2  - conferenceId
    StringType,  # 3  - accessLevel
    StringType,  # 4  - displayName
    StringType,  # 5  - connectionState
    ListType,    # 6  - calls
    ListType,    # 7  - addresses
]
conferenceInformationCache        = []
activeParticipantInformationCache = []

fileLock = threading.Lock()


class Call():
    def __init__(self, participantId, active, conferenceId, accessLevel, displayName, connectionState, calls,
                 addresses):
        self.participantId = participantId
        self.active = active
        self.conferenceId = conferenceId
        self.accessLevel = accessLevel
        self.displayName = displayName
        self.connectionState = connectionState
        self.calls = calls
        self.addresses = addresses
        print('Call created with participantId: %s' % self.participantId )

    def insertCall(self):
        # We insert the call so we can assume format is correct
        logging.info('insertCall() Inserting new call | participantId: %s' % self.participantId)
        newRecord = self.participantId + ',' + \
                    str(self.active) + ',' + \
                    self.conferenceId + ',' + \
                    self.accessLevel + ',' + \
                    self.displayName + ',' + \
                    self.connectionState + ',' + \
                    str(self.calls) + ',' + \
                    str(self.addresses)
        threadWrite = ReadWriteFileThread("insertCall() Thread-Write", 3, systemParticipantList, "a+", newRecord)
        threadWrite.start()
        threadWrite.join()


###########################################################################################
# Handle XMLRequests from each Feedback Configure requests
###########################################################################################
class Subject():
    #@abstractmethod
    def register_observer(Observer):
        """Registers an observer with Subject."""
        pass

    #@abstractmethod
    def remove_observer(Observer):
        """Removes an observer from Subject."""
        pass

    #@abstractmethod
    def notify_observers(Observer):
        """Notifies observers that Subject data has changed."""
        pass


class Observer():
    def __init__(self):
        self.updated = False

    def update(self):
        self.updated = True


###########################################################################################
# XML Core
###########################################################################################

# Singleton
class feedBackServer():
    def __init__(self, uri, port, active):
        self.uri = uri
        self.port = port
        self.active = active

    def getPort(self):
        return self.port

    def setActiveStatus(self, status):
        self.active = status


class feedBackServerNotifier():
    def notify(self):
        logging.info('Notifying feedback Servers')


###########################################################################################
# Handle XMLRequests and client login
###########################################################################################

class XmlRequestHandler(SimpleXMLRPCRequestHandler):
    # Restrict to a particular path.
    rpc_paths = ('/RPC2',)

    def do_POST(self):
        clientIP, port = self.client_address
        # Log client IP and Port
        logging.info('Client IP: %s - Port: %s' % (clientIP, port))
        try:
            data = self.rfile.read(int(self.headers["content-length"]))
            logging.info('Client request: \n%s\n' % data)
            response = self.server._marshaled_dispatch(data, getattr(self, '_dispatch', None))
            logging.info('Server response: \n%s\n' % response)
        except:  # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)
            self.end_headers()
            logging.error('Internal error')
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)


###########################################################################################
# Handle file reads and multithreading
###########################################################################################

#threadWrite = ReadWriteFileThread("Thread-Write",2,systemConfigurationFile,"a",newRecord)
class ReadWriteFileThread(threading.Thread):
    def __init__(self, name, threadID, FileName, Operation, Record):
        threading.Thread.__init__(self)
        self.name = name
        self.threadID = threadID
        self.FileName = FileName
        self.Operation = Operation
        self.Record = Record
        #print ('ReadWriteFileThread() File name: ' + FileName)

    def run(self):
        #print "Starting " + self.name + " " + str(self.threadID)
        fileLock.acquire()
        #Read file
        if (self.Operation == "r"):
            try:
                with open(self.FileName, self.Operation) as config_file:
                    try:
                        fileRecords = csv.reader(config_file, delimiter=',', skipinitialspace=True)
                        allRecords = [record for record in fileRecords]
                    finally:
                        #print 'ReadWriteFileThread() Close file'
                        config_file.close();
                        #Check file format
                        if self.FileName == systemConferenceList:
                            if validateDataFromFile(allRecords, 1, False) == -1:
                                return -1
                            else:
                                return 0
                        elif self.FileName == systemParticipantList:
                            # During API call we need to read cache
                            logging.info("Reading active participant list")
                            if validateDataFromFile(allRecords, 2, False) == -1:
                                return -1
                            else:
                                return 0
                        else:
                            logging.error('Invalid file reference')
                            return -1
            except IOError:
                config_file.close();
                pass
        #Add record to file
        elif (self.Operation == "a+"):
            try:
                with open(self.FileName, self.Operation) as config_file:
                    try:
                        config_file.write(self.Record + '\n')
                    finally:
                        config_file.close();
                        #print 'ReadWriteFileThread() Close file'
            except IOError:
                print 'ReadWriteFileThread() IOError Close file'
                config_file.close();
                pass
        else:
            print "ReadWriteFileThread() Invalid operation: " + str(self.Operation)
        fileLock.release()


###########################################################################################
# System configuration
###########################################################################################
def initializeSystem():
    systemMode = getSystemMode()
    initResult = readConferenceFileConfiguration()
    #initResult = 0

    if initResult == -1:
        print "Error invalid configuration"
        logging.error("_init_() Error invalid configuration")
        print "Program exiting...."
        logging.error("_init_() Program exiting....")
        raise SystemExit
    elif initResult == -2:
        print "Error invalid records detected"
        logging.error("_init_() Error invalid records detected")
        print "Program exiting...."
        logging.error("_init_() Program exiting....")
        raise SystemExit
    else:
        return


#############################################################################################

# Run the server's main loop
def startXmlRpc():
    logging.info("Cisco TelePresence Server 8710 Emulator started....")
    print "Cisco TelePresence Server 8710 Emulator started...."
    logging.info("Hostname: " + hostname + " Port: " + str(port))
    print "Hostname: " + hostname + " Port: " + str(port)
    logging.info("API Version:  " + version)
    print "API Version:  " + version
    try:
        logging.info("XML-RPC Server initialized...")
        threading.Thread(target=server.serve_forever()).start()
    except KeyboardInterrupt:
        logging.info("Cisco TelePresence Server 8710 Emulator stopping xml service....")
    except Exception as instance:
        print type(instance)
        print instance.args
        logging.error("startXmlRpc() Exception: " + str(instance))
        raise SystemExit


#############################################################################################
# Initilize server information

def feedbackReceiverInitialize():
    # Observer pattern
    global feedbackReceiverIndex
    feedbackReceiverIndex = range(1, 100, 1)


#############################################################################################

### Return SystemMode and configuration options from system.xml
def getSystemMode(*args, **kwargs):
    from xml.dom import minidom

    doc = minidom.parse(systemConfigurationFile)
    # doc.getElementsByTagName returns NodeList
    # Get specific parameter
    if len(args) == 1:
        try:
            name = doc.getElementsByTagName("system")[0]
            paramValue = doc.getElementsByTagName(args[0])[0]
            if paramValue:
                return paramValue.firstChild.data
            else:
                return -1
        except:
            pass
            return -1
    # Normal Mode
    elif len(args) == 0:
        try:
            name = doc.getElementsByTagName("system")[0]
            print(name.firstChild.data)
            systemModeInFile = doc.getElementsByTagName("mode")[0]
            if systemModeInFile == "flex":
                logging.info("Flex Mode activated" + systemModeInFile.firstChild.data)
                return 0
                # This is flex mode
            elif systemModeInFile == "local":
                return 1
            else:
                return -1
        except:
            pass
            return -1
    else:
        return -1


#############################################################################################

def getActiveCallsFromFile():
    global activeCallsInFile
    logging.info('insertActiveCallsToFile() total number of active calls: ' + str(len(activeCalls)))


#############################################################################################

def insertActiveCallsToFile():
    global activeCalls
    logging.info('insertActiveCallsToFile() total number of active calls: ' + str(len(activeCalls)))
    for call in activeCalls:
        call.insertCall()


#############################################################################################

def callGenerator(maxCalls):
    logging.info('callEmulator() emulating Calls: ' + maxCalls)
    maxCalls = convertStr(maxCalls)
    if maxCalls > 0:
        logging.info('callEmulator() Creating calls...')
        for call in range(1, maxCalls + 1):
            #def __init__(self, participantId, active, conferenceId, accessLevel, displayName, connectionState, calls,addresses):
            #participantID,conferenceID,accessLevel,displayName,connectionState,calls,addresses
            #78eb3250-632f-11e4-b642-000d7c10b020,ab3798b0-4dbe-11e4-b63f-000d7c10b020,chair,ATT-Ops-SUT-1000,connected,{callID:'78eb0b40-632f-11e4-b642-000d7c10b020',incoming:True,address:'11111112130'},{URI:'9002'}
            participantId = generateNewParticipantId()
            active = True
            conferenceId = getConferenceGUID()
            accessLevel = 'chair'
            displayName = 'endpoint-' + str(call)
            connectionState = 'connected'
            calls = {'callID': participantId, 'incoming': True, 'address': '1111111000' + str(call)}
            addresses = {'URI': '900' + str(call)}
            logging.info('Creating call (' + str(call) + ')')
            newCall = Call(participantId, active, conferenceId, accessLevel, displayName, connectionState, calls,
                           addresses)
            # Insert new calls
            activeCalls.append(newCall)


#############################################################################################

def getConferenceGUID():
    return getSystemMode('conferenceGUID')


#############################################################################################

def startCallServer():
    logging.info("Starting call emulator services...")
    print "Starting call emulator services..."
    if getSystemMode("callControl") == 'True':
        logging.info('Call emulator started succesfully')
        print "Call emulator started succesfully."
        callGenerator(getSystemMode("maxCalls"))
        insertActiveCallsToFile()
        #cc = Process(target=insertActiveCallsToFile(), args=())
        #cc.start()
        #cc.join()
    else:
        logging.error('Call emulator service failed to start')
        print "Call emulator service failed to start'"


#############################################################################################

# Read configuration file
# configuration.xml contains conference information
def readConferenceFileConfiguration():
    logging.info("Reading system conference file: " + systemConferenceList)
    try:
        with open(systemConferenceList, "r") as config_file:
            try:
                fileRecords = csv.reader(config_file, delimiter=',', skipinitialspace=True)
                allRecords = [record for record in fileRecords]
            finally:
                config_file.close();
                # Validate headers in conference configuration file
                if validateConferenceParametersInFile(allRecords) == -1:
                    return -1
                # Validate conference records
                if validateConferenceData(allRecords) == -1:
                    return -2
    except IOError:
        pass

#############################################################################################
# Verify configuration parameters in file
def validateConferenceParametersInFile(fileparams):
    for param in fileparams[0]:
        if param in configParameters:
            logging.info('validateConferenceParametersInFile() Valid parameter: ' + param)
        else:
            logging.info('validateConferenceParametersInFile() Invalid parameter: ' + param)
            return -1

#############################################################################################
#Stores information from conference file
#conferenceID,conferenceGUID,numericID

def updateConferenceInformation(conferenceID, conferenceGUID, numericID):
    if castRecordElement(conferenceID) == conferenceFieldDataType[6] and castRecordElement(conferenceGUID) == conferenceFieldDataType[
        10] and castRecordElement(numericID) == conferenceFieldDataType[16]:
        conferenceInformationCache.append({int(conferenceID), conferenceGUID, int(numericID)})
        logging.info(
            "updateConferenceInformation() Valid record " + conferenceID + " " + conferenceGUID + " " + numericID)
        return True
    else:
        logging.error(
            "updateConferenceInformation() Invalid record " + conferenceID + " " + conferenceGUID + " " + numericID)
        return False


#############################################################################################

# Verify records in file
def validateConferenceData(fileRecords):
    logging.info("Validating Conference data...")
    #file_lines(configurationFile)
    logging.info(
        "validateConferenceData() Processing " + str(readFileLines(systemConferenceList) - 1) + " record(s)...")
    # Delete header line
    del fileRecords[0]
    # Copy fileRecords to global conferenceRecordsInFile
    global conferenceRecordsInFile
    conferenceRecordsInFile = copy.copy(fileRecords)
    if len(fileRecords) < 1:
        return -1
    for record in fileRecords:
        logging.info("validateConferenceData() " + str(record))
        paramNumber = 0
        # conference record line contains 28 fields
        if len(record) == 28:
            for field in record:
                if paramNumber == 12 and field == "''":  # No PIN
                    paramNumber += 1
                elif castRecordElement(field) == conferenceFieldDataType[paramNumber]:
                    if paramNumber == 6:
                        conferenceID = field
                    if paramNumber == 10:
                        conferenceGUID = field
                    if paramNumber == 16:
                        numericID = field
                    paramNumber += 1
            else:
                if paramNumber != 28:
                    logging.info("validateConferenceData() Invalid data paramNumber: " + str(paramNumber))
                    return -1
            # Populate conference information
            updateConferenceInformation(conferenceID, conferenceGUID, numericID)
        else:
            logging.warning("validateConferenceData() Invalid record: " + record)
            return -1


#############################################################################################


def updateParticipantInformation(participantID, active, conferenceID, accessLevel, displayName, connectionState,calls,addresses):
     if castRecordElement(participantID) == participantFieldDataType[0] and castRecordElement(conferenceID) == participantFieldDataType[2] and castRecordElement(displayName) == participantFieldDataType[4]:
        activeParticipantInformationCache.append({participantID, conferenceID, accessLevel,displayName,connectionState,calls,addresses})
        logging.info("updateParticipantInformation() Valid record inserted into cached: " + str(participantID) + " " + str(conferenceID) + " " + str(displayName))
        return True
     else:
        logging.error("updateParticipantInformation() Invalid record " + str(participantID) + " " + str(conferenceID) + " " + str(displayName))
        return False

#############################################################################################


#Verify credentials are correct
# TODO MD5 checksum + SALT

def authenticationModule(username, password):
    if len(username) > 128 or len(password) > 128:
        return False
    if username == systemUserName and password == systemPassWord:
        return True
    else:
        return False


#############################################################################################

# Return number of lines in file
def readFileLines(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1



#############################################################################################

def readActiveParticipants(fileRecords):
    #file_lines(configurationFile)
    logging.info(
        "readActiveParticipants() Processing " + str(readFileLines(systemConferenceList) - 1) + " record(s)...")
    del fileRecords[0]
    activeCalls = copy.copy(fileRecords)

    if len(activeCalls) < 1:
        return -1
    for call in activeCalls:
        logging.info("readActiveParticipants()" + str(call))
        paramNumber = 0
        if len(call) == 7:
            for field in call:
                paramNumber += 1
        else:
            logging.warning("readActiveParticipants() Invalid Record: " + call)
            return -1


#############################################################################################

# Verify records in file
def validateDataFromFile(fileRecords, type, check):
    #file_lines(configurationFile)
    logging.info("validateDataFromFile() Processing record(s)...")
    # Delete first line which includes header
    del fileRecords[0]
    # Copy fileRecords to global conferenceRecordsInFile
    global conferenceRecordsInFile
    conferenceRecordsInFile = copy.copy(fileRecords)
    if len(fileRecords) < 1:
        return -1
    # Conferences
    if type == 1:
        if check:
            for record in fileRecords:
                logging.info("validateDataFromFile() Conference: " + str(record))
                paramNumber = 0
                if len(record) == 28:
                    for field in record:
                        if paramNumber == 12 and field == "''":  # No PIN
                            paramNumber += 1
                        elif castRecordElement(field) == conferenceFieldDataType[paramNumber]:
                            if paramNumber == 6:
                                conferenceID = field
                            if paramNumber == 10:
                                conferenceGUID = field
                            if paramNumber == 16:
                                numericID = field
                            paramNumber += 1
                    else:
                        if paramNumber != 28:
                            logging.info("validateDataFromFile() Invalid data paramNumber: " + str(paramNumber))
                            return -1
                    updateConferenceInformation(conferenceID, conferenceGUID, numericID)
                else:
                    logging.warning("validateDataFromFile() Invalid record: " + record)
                    return -1
    # Participants
    elif type == 2:
        if check:
            for record in fileRecords:
                logging.info("validateDataFromFile() Participant info: " + str(record))
                paramNumber = 0
                if len(record) == 8:
                    for field in record:
                        if paramNumber == 4 and field == "''":  # No displayName
                            paramNumber += 1
                        elif castRecordElement(field) == participantFieldDataType[paramNumber]:
                            if paramNumber == 0:
                                participantID = field
                            if paramNumber == 1:
                                active = field
                            if paramNumber == 2:
                                conferenceID = field
                            if paramNumber == 3:
                                accessLevel = field
                            if paramNumber == 4:
                                displayName = field
                            if paramNumber == 5:
                                connectionState = field
                            if paramNumber == 6:
                                calls = field
                            if paramNumber == 7:
                                addresses = field
                        else:
                            logging.error("validateDataFromFile() Invalid param ( " + str(paramNumber) + "):  " + str(field))
                        paramNumber += 1
                    else:
                        if paramNumber != 8:
                            logging.info("validateDataFromFile() Invalid data paramNumber: " + str(paramNumber))
                            return -1
                    updateParticipantInformation(participantID, active, conferenceID, accessLevel, displayName, connectionState,
                                                 calls,addresses)
                else:
                    logging.warning("validateDataFromFile() Invalid record: " + record)
                    return -1
        else:
            # No check
            for record in fileRecords:
                logging.info("validateDataFromFile() Participant: " + str(record))
                paramNumber = 0
                for field in record:
                    if paramNumber == 0:
                        participantID = field
                    if paramNumber == 1:
                        active = field
                    if paramNumber == 2:
                        conferenceID = field
                    if paramNumber == 3:
                        accessLevel = field
                    if paramNumber == 4:
                        displayName = field
                    if paramNumber == 5:
                        connectionState = field
                    if paramNumber == 6:
                        calls = field
                    if paramNumber == 7:
                        addresses = field
                    paramNumber += 1
                updateParticipantInformation(participantID, active, conferenceID, accessLevel, displayName, connectionState,calls,addresses)
    else:
        return -1


#############################################################################################

#Verifies authentication and returns remaining parameters specified in structure
def xml_RequestHandler(msg):
    username = ""
    password = ""
    params = copy.deepcopy(msg)
    # Verify authentication and then collect other parameters
    for element in params:
        if element == 'authenticationUser':
            username = msg.get('authenticationUser')
        if element == 'authenticationPassword':
            password = msg.get('authenticationPassword')

    if username == "" or password == "":
        logging.error("Invalid credentials")
        return 101
    if (authenticationModule(username, password)):
        del params['authenticationUser']
        del params['authenticationPassword']
        return params
    else:
        return 34


#############################################################################################

#Read file and update conferenceInformationCache
def updateConfigurationInfo():
    print "updateConfigurationInfo() Updating cache...."
    logging.info("updateConfigurationInfo: " + systemConferenceList)
    threadRead = ReadWriteFileThread("Thread-Read", 1, systemConfigurationFile, "r", "")
    threadRead.start()
    #threadRead.join()


#############################################################################################

#Find param X in conference record
def findParameterInConference(param):
    if param >= 0 and param < len(conferenceParameters):
        return conferenceParameters[param]
    else:
        return -1


#############################################################################################

#Create conference record based on create_recordby_conferenceName
def createConferenceByConferenceName(msg):
    maxAttempts = 50
    attempts = 0
    validnewRecord = False
    xmlResponse = []

    print msg
    params = copy.deepcopy(msg)
    conferenceName = ''
    # Verify authentication and then collect other parameters
    for element in params:
        if element == 'conferenceName':
            conferenceName = params.get('conferenceName')

    # 	Verify conferenceName status
    logging.info("createConferenceByConferenceName(): " + conferenceName)
    #   Add '' to conferenceName in case is not coming like that
    if conferenceName.find("'") == -1:
        conferenceName = "'" + conferenceName + "'"

    if len(conferenceName) > 80 and not isinstance(conferenceName, str):
        return -1

    logging.info("createConferenceByConferenceName() Creating new conference...")
    conferenceID = generateNewConferenceID()
    conferenceGUID = generateNewConferenceGUID()
    numericID = generateNewNumericID()
    logging.info("createConferenceByConferenceName() New conferenceID: " + str(conferenceID))
    logging.info("createConferenceByConferenceName() New conferenceGUID: " + str(conferenceGUID))
    logging.info("createConferenceByConferenceName() New numericID: " + str(numericID))

    if len(conferenceGUID) != 36 and not isinstance(conferenceGUID, str):
        return -1

    while (not validnewRecord and attempts < maxAttempts):
        if conferenceID > 10000 or numericID > 10000:
            return -1
            break
        resultValidation = validateNewRecord(conferenceID, conferenceGUID, numericID)
        if resultValidation == -1:
            validnewRecord = False
            return -1
        elif resultValidation == -2:
            conferenceID = generateNewConferenceID()
            attempts += 1
        elif resultValidation == -3:
            numericID = generateNewNumericID()
            attempts += 1
        else:
            validnewRecord = True
            break

    if attempts >= maxAttempts:
        return -1

    newRecord = "24,False,0,10,False,0," + str(
        conferenceID) + ",True,24,0," + "'" + conferenceGUID + "'" + ",False,'',True,False,True," + str(
        numericID) + ",[],False,True,0," + conferenceName + ",'',False,'',False,0,0"
    threadWrite = ReadWriteFileThread("Thread-Write", 2, systemConfigurationFile, "w", newRecord)
    threadWrite.start()
    threadWrite.join()
    xmlResponse.append(conferenceGUID)
    xmlResponse.append(numericID)
    conferenceInformationCache.append({conferenceID, conferenceGUID, numericID})
    return xmlResponse


#############################################################################################

#Find conference record based on conferenceGUID
def findRecordByConferenceGUID(msg):
    print msg
    params = copy.deepcopy(msg)
    conferenceGUID = ''
    updateConfigurationInfo()

    # Verify authentication and then collect other parameters
    for element in params:
        if element == 'conferenceGUID':
            conferenceGUID = params.get('conferenceGUID')

    # 	Verify conferenceGUID status
    #   logging.info("findRecordByConferenceGUID: " + conferenceGUID)
    #   Add '' to conferenceGUID in case is not coming like that
    if conferenceGUID.find("'") == -1:
        conferenceGUID = "'" + conferenceGUID + "'"

    if len(conferenceGUID) != 36 and not isinstance(conferenceGUID, str):
        return -1
    else:
        if len(conferenceRecordsInFile) < 1:
            return -1
        else:
            for record in conferenceRecordsInFile:
                paramNumber = 0
                for field in record:
                    if paramNumber == 10:
                        if field == conferenceGUID:
                            logging.info("findRecordByConferenceGUID() " + conferenceGUID)
                            return record
                    else:
                        paramNumber += 1
    return -1


#############################################################################################

def generateNewParticipantId():
    #78eb3250-632f-11e4-b642-000d7c10b020
    return random_string(8) + "-" + random_string(4) + "-" + random_string(4) + "-" + random_string(
        4) + "-" + random_string(12)


#############################################################################################

# Generate random conference ID
def generateNewConferenceGUID():
    #ab3798b0-4dbe-11e4-b63f-000d7c10b020
    return random_string(8) + "-" + random_string(4) + "-" + random_string(4) + "-" + random_string(
        4) + "-" + random_string(12)


#############################################################################################

# Generate random conferenceID
def generateNewConferenceID():
    return randrange(1000, 9999)


# Generate random numeric ID
def generateNewNumericID():
    return randrange(1000, 9999)


#############################################################################################

def validateNewRecord(conferenceID, conferenceGUID, numericID):
    for element in conferenceInformationCache:
        for item in element:
            if conferenceGUID == item:
                return -1
            if conferenceID == item:
                return -2
            if numericID == item:
                return -3
    return 0


#############################################################################################

def createXmlResponse(args):
    xmlResponse = {'conferenceName': 'AT&T TelePresence Solution connection test', 'conferenceID': 45966,
                   'conferenceGUID': '6b30aed0-be06-11e2-af9d-000d7c112b10', 'active': True, 'persistent': False,
                   'locked': False,
                   'numericID': 8100, 'registerWithGatekeeper': False, 'registerWithSIPRegistrar': False,
                   'h239ContributionEnabled': False, 'pin': ''}
    return xmlResponse


###########################################################################################
# System utilities
###########################################################################################

def convertStr(s):
    """Convert string to either int or float."""
    try:
        ret = int(s)
    except ValueError:
        #Try float.
        ret = float(s)
    return ret


# Generate random String
def random_string(length):
    chars = set(string.ascii_lowercase + string.digits)
    char_gen = (c for c in imap(urandom, repeat(1)) if c in chars)
    return ''.join(islice(char_gen, None, length))


# Logging info
def logInfo(msg):
    logging.info(msg)


# Cast value from string
def boolify(s):
    if s == 'True' or s == 'true':
        return True
    if s == 'False' or s == 'false':
        return False
    raise ValueError('Not Boolean Value!')


def noneify(s):
    ''' for None type'''
    if s == 'None': return None
    raise ValueError('Not None Value!')


def listify(s):
    '''will convert a string representation of a list
    into list of homogenous basic types.  type of elements in
    list is determined via first element and successive 
    elements are casted to that type'''

    #this cover everything?
    if "," not in s:
        raise ValueError('Not a List')


    #derive the type of the variable
    loStrings = s.split(',')
    elementCaster = None
    for caster in (boolify, int, float, noneify, str):
        try:
            caster(loStrings[0])
            elementCaster = caster
            break
        except ValueError:
            pass

    #cast all elements
    try:
        castedList = [elementCaster(x) for x in loStrings]
    except ValueError:
        raise TypeError("Autocasted list must be all same type")

    return castedList


def estimateTypedValue(var):
    '''guesses the str representation of the variable's type'''

    #dont need to guess type if it is already un-str typed (not coming from CLI)
    if type(var) != type('aString'):
        return var

        #guess string representation, will default to string if others dont pass
    for caster in (boolify, int, float, noneify, listify, str):
        try:
            return caster(var)
        except ValueError:
            pass


def autocast(dFxn):
    def wrapped(*c, **d):
        cp = [estimateTypedValue(x) for x in c]
        dp = dict((i, estimateTypedValue(j)) for (i, j) in d.items())
        return dFxn(*cp, **dp)

    return wrapped


@autocast
def castRecordElement(element):
    if element == "[]":
        return ListType
    elif element == "{}":
        return DictionaryType
    else:
        return type(element)


###########################################################################################
# API Method implementation
###########################################################################################

def ping_function(msg):
    logInfo("ping_function() API ping")
    if msg == 'REQUEST':
        return 'REPLY'
    else:
        return 'INVALID MESSAGE: ' + msg


def conference_create(msg):
    logInfo("conference_create() API conference.create")
    params = xml_RequestHandler(msg)
    xmlResponse = []

    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        xmlResponse = createConferenceByConferenceName(params)
        if (xmlResponse != -1 and len(xmlResponse) >= 2):
            print "conference_create() API conference.create New conferenceGUID: " + xmlResponse[0]
            logInfo(xmlResponse)
            xmlResponse = {'conferenceGUID': xmlResponse[0], 'numericID': xmlResponse[1]}
            return xmlResponse
        else:
            return fault_code(systemErrors[201], 201)


def conference_delete(msg):
    return msg


def conference_enumerate(msg):
    # 	Optional params could be:
    #					enumerateID  integer
    #					activeFilter boolean
    #	conferenceName,conferenceID,conferenceGUID,active,persistent,locked,numericID,registerWithGatekeeper,registerWithSIPRegistrar,h239ContributionEnabled,pin
    logInfo("conference_enumerate() API conference.enumerate")
    xmlResponse = {'conferenceName': 'AT&T TelePresence Solution connection test', 'conferenceID': 45966,
                   'conferenceGUID': '6b30aed0-be06-11e2-af9d-000d7c112b10', 'active': True, 'persistent': False,
                   'locked': False,
                   'numericID': 8100, 'registerWithGatekeeper': False, 'registerWithSIPRegistrar': False,
                   'h239ContributionEnabled': False, 'pin': ''}
    return xmlResponse


def conference_invite(msg):
    return msg


def conference_senddtmf(msg):
    return msg


def conference_sendmessage(msg):
    return msg


def conference_sendwarning(msg):
    return msg


def conference_set(msg):
    return msg


def conference_status(msg):
    # 	Verify conferenceGUID status
    #	Todo re-readFile for new conferences added
    logInfo("conference_status() API conference.status ")
    params = xml_RequestHandler(msg)
    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        xmlResponse = findRecordByConferenceGUID(params)
        if (xmlResponse != -1):
            logInfo(xmlResponse)
            return xmlResponse
        else:
            return fault_code(systemErrors[4], 4)


def conference_uninvite(msg):
    return msg


def fault_code(string, code):
    xmlResponse = {'faultCode': code, 'faultString': string}
    logInfo(xmlResponse)
    return xmlResponse


# Flex Mode methods
def feedbackReceiver_configure(msg):
    print("feedbackReceiver() API feedbackReceiver.configure")
    logInfo("feedbackReceiver() API feedbackReceiver.configure")
    params = xml_RequestHandler(msg)
    receiverURI = ''

    if (params == 34):
        logging.error('feedbackReceiver() xml_RequestHandler error')
        return fault_code(systemErrors[34], 34)

    for element in params:
        if element == 'receiverURI':
            receiverURI = params.get('receiverURI')
        if element == 'receiverIndex':
            receiverIndex = params.get('receiverIndex')

    logging.info('feedbackReceiver() receiverURI: ' + receiverURI)
    #ReceiverIndex was not in params will be assigned from pool
    if receiverIndex == -1:
        receiverIndex = feedbackReceiverIndex[0]
        logging.info('feedbackReceiver() receiverIndex -1: Generating new value: ' + str(receiverIndex))
    elif not receiverIndex:
        receiverIndex = feedbackReceiverIndex[0]
        logging.info('feedbackReceiver() Generating new value: ' + str(receiverIndex))
    else:
        logging.info('feedbackReceiver() receiverIndex: ' + str(receiverIndex))

    if not feedbackReceiverIndex[0]:
        # Not enough indexes
        logging.error('feedbackReceiver() not enough indexes')
        return fault_code(systemErrors[34], 34)

    # Get port from URL
    port = urlparse(receiverURI).port

    # URI and port MUST exist
    if receiverURI and port:
        logging.info('feedbackReceiver() Creating feebackReceiver receiverURI: ' + receiverURI)
        logging.info('feedbackReceiver() Feedback client port: ' + str(port))
    else:
        logging.error('feedbackReceiver() Invalid request')
        return fault_code(systemErrors[34], 34)

    # Create new Feedback Receiver object
    feedbackServerInstance = feedBackServer(receiverURI, port, True)
    # Check Object does not exist in FeedBack receiver
    if not feedBackServerList.has_key(receiverIndex):
        feedBackServerList[receiverIndex] = feedbackServerInstance
    else:
        # TODO allocate an index not in use, do it more nicely
        return fault_code(systemErrors[6], 6)

    xmlResponse = []
    # Operation is succesful
    xmlResponse = {'status': 'operation succesful', 'receiverIndex': receiverIndex}
    # Get rid of index as its in use
    try:
        del feedbackReceiverIndex[0]
    except:
        pass

    return xmlResponse


def getCookieValue():
    #Generate random string:
    return '265;0;' + random_string(3)


def getActiveParticipantList():
    """
        [
        {'participantId': 'b3fk365k-3c33-xlce-sc8f-85yxb1kvx621',
        'conferenceId': '8ca0c690-dd82-11e2-84f9-000d7c112b10',
        'accessLevel': 'chair',
        'displayName': 'endpoint-1',
        'connectionState': 'connected',
        'calls': {'callID': 'b3fk365k-3c33-xlce-sc8f-85yxb1kvx621', 'incoming': True, 'address': '11111110001'},
        'addresses': {'URI': '9001'}
        }
        ]
    """
    print "readActiveParticipantsFromFile() Updating cache...."
    logging.info("readActiveParticipantsFromFile: " + systemParticipantList)
    threadRead = ReadWriteFileThread("Thread-Read", 2, systemParticipantList, "r", "")
    threadRead.start()
    threadRead.join()
    if activeParticipantInformationCache:
        for participant in activeParticipantInformationCache:
            print participant

    else:
        logging.error("No active participants obtained from cached")

def flex_participant_enumerate(msg):
    logInfo("flex_participant_enumerate() API flex.participant.enumerate")
    # Optional parameters:
    # cookie
    # max
    # conferenceID
    params = xml_RequestHandler(msg)
    xmlResponse = []

    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        #xmlResponse = getActiveParticipantList()
        getActiveParticipantList()
        #print str(xmlResponse)
        xmlResponse = 'getActiveParticipantList...'
        participantsInfo = [{'participantId': 'b3fk365k-3c33-xlce-sc8f-85yxb1kvx621',
                             'conferenceId': '8ca0c690-dd82-11e2-84f9-000d7c112b10',
                             'accessLevel': 'chair',
                             'displayName': 'endpoint-1',
                             'connectionState': 'connected',
                             'calls': {'callID': 'b3fk365k-3c33-xlce-sc8f-85yxb1kvx621', 'incoming': True,'address': '11111110001'},
                             'addresses': {'URI': '9001'}}]

        cookieValue = getCookieValue()
        moreAvailable = 'moreAvailable'

        if (xmlResponse != -1 and len(xmlResponse) >= 2):
            logInfo(xmlResponse)
            xmlResponse = {'Cookie': cookieValue, 'moreAvailable': False, 'participants': participantsInfo}
            return xmlResponse
        else:
            return fault_code(systemErrors[201], 201)


# Register an instance; all the methods of the instance are published as XML-RPC methods (in this case, just 'div').
class Methods:
    def show_version(self):
        print("show_version() API show.version")
        logInfo("show_version() API show.version")
        return version

# Create server
server = SimpleXMLRPCServer((hostname, port), requestHandler=XmlRequestHandler, logRequests=True)
server.register_function(ping_function, 'ping')

"""if systemMode==0:
        server.register_function(conference_create, 'conference.create')
        server.register_function(conference_delete, 'conference.delete')
        server.register_function(conference_enumerate, 'conference.enumerate')
        server.register_function(conference_invite, 'conference.invite')
        server.register_function(conference_senddtmf, 'conference.senddtmf')
        server.register_function(conference_sendmessage, 'conference.sendmessage')
        server.register_function(conference_sendwarning, 'conference.sendwarning')
        server.register_function(conference_set, 'conference.set')
        server.register_function(conference_status, 'conference.status')
        server.register_function(conference_uninvite, 'conference.uninvite')"""

server.register_function(feedbackReceiver_configure, 'feedbackReceiver.configure')
server.register_function(flex_participant_enumerate, 'flex.participant.enumerate')
server.register_instance(Methods())


# Main function
def telepresenceServer():
    logging.basicConfig(filename='logs/telepresence.log', level=logging.INFO,
                        format='%(asctime)s.%(msecs).03d %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.info("-----------------------Initializing server------------------------")
    print "-----------------------Initializing server------------------------"
    try:
        initializeSystem()
        feedbackReceiverInitialize()
        xml = Process(target=startXmlRpc)
        cc = Process(target=startCallServer)
        # Start xmlServer and CallServer
        xml.start()
        cc.start()
        xml.join()
        cc.join()
    except KeyboardInterrupt:
        print "Cisco TelePresence Server 8710 Emulator stopping...."
        logging.info("Cisco TelePresence Server 8710 Emulator stopping....")
    except Exception, e:
        print "Exception found" + str(e)
        logging.error("Exception found " + str(e))


if __name__ == '__main__':
    telepresenceServer()
