'''
@author Gonzalo Gasca Meza
		AT&T Labs 
		Date: November 2014
		Purpose: Emulates TelePresence Server 8710 Server API
'''

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from threading import Thread
from multiprocessing import Process,JoinableQueue,Value,Lock
from os import urandom
from random import randrange
from itertools import islice, imap, repeat
from types import *
from urlparse import urlparse
from random import randint
import time, string, csv, threading, logging, copy, re,os
import xmlrpclib
import requests

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
callsGenerated = []
feedBackServerList = {}
feedBackServerListQueue = JoinableQueue(100)    # 100 is Max Feedback receivers instances
feedbackReceiverIndex = []
staticSUTEndpoints = []
participantMediaStatistics = {}                 # This array adds participants Media information
lock = Lock()
counter = Value('i', 1)

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
    BooleanType, # 0
    StringType,  # 1  - participantId
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
    def __init__(self, active,participantId,conferenceId, accessLevel, displayName, connectionState, calls,
                 addresses):
        self.active = active
        self.participantID = participantId
        self.conferenceId = conferenceId
        self.accessLevel = accessLevel
        self.displayName = displayName
        self.connectionState = connectionState
        self.calls = calls
        self.addresses = addresses
        print('Call() _init_ instance created participantID: %s' % self.participantID )

    def insertCall(self):
        # We insert the call so we can assume format is correct
        try:
            logging.info('Call.insertCall() Inserting new call | participantID: %s' % self.participantID)
            newRecord = str(self.active) + ',' + \
                        self.participantID + ',' + \
                        self.conferenceId + ',' + \
                        self.accessLevel + ',' + \
                        self.displayName + ',' + \
                        self.connectionState + ',' + \
                        str(self.calls) + ',' + \
                        str(self.addresses)
            threadWrite = ReadWriteFileThread("insertCall() Thread-Write", 3, systemParticipantList, "a+", newRecord)
            threadWrite.start()
            threadWrite.join()
        except Exception,e:
            logging.exception('Call.insertCall()' + str(e))

    def getParticipantId(self):
        return self.participantID

    def getCallStatus(self):
        return self.active

###########################################################################################

class Counter(object):
    def __init__(self, initval=0):
        self.val = Value('i', initval)
        self.lock = Lock()

    def increment(self):
        with self.lock:
            self.val.value += 1

    def value(self):
        with self.lock:
            return self.val.value

###########################################################################################
# XML Core
###########################################################################################

# Singleton
class feedBackServer():

    def __init__(self, uri=None, port=None, active=None):
        self.uri = uri
        self.port = port
        self.active = active
        self.notifier = feedBackServerNotifier(self.uri,self.port,self.active)
        # Create object to send Keepalive

    def getKeepAliveInstance(self):
        return self.notifier

    def getPort(self):
        return self.port

    def setActiveStatus(self, status):
        self.active = status

    def __str__(self):
        return str(self.uri)

###########################################################################################

class feedBackServerNotifier():
    def __init__(self, uri, port, active):
        self.uri = uri
        self.port = port
        self.active = active

    def keepAlive(self,option):
        events = []
        logging.info('feedBackServerNotifier.keepAlive() Notifying feedback Servers')
        if option == 'configureAck' or option == 'flexAlive':
            print 'feedBackServerNotifier.keepAlive(): ' + option
            logging.info('feedBackServerNotifier.keepAlive(): ' + option)
            events.append(option)
        else:
            logging.error('feedBackServerNotifier.keepAlive() Invalid option')
            events.append('keepAlive')

        parameters = {'sourceIdentifier': 'TEMPSRCID','events': events}
        params = tuple([parameters])
        xmlrpccall = xmlrpclib.dumps(params,'eventNotification',encoding='UTF-8')
        response = requests.request( 'POST', self.uri,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100,
                             stream = False, )
        if response.status_code == 200:
            result = xmlrpclib.loads( response.content, )[ 0 ]
            events = []
        else:
  	        print '(feedBackServerNotifier) Error'
  	        return -1


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
                        config_file.close();
                        fileLock.release()
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
                fileLock.release()
                config_file.close();
                pass
        #Add record to file
        elif (self.Operation == "a+"):
            try:
                with open(self.FileName, self.Operation) as config_file:
                    try:
                        config_file.write(self.Record + '\n')
                    finally:
                        fileLock.release()
                        config_file.close();
                        #print 'ReadWriteFileThread() Close file'
            except IOError:
                print 'ReadWriteFileThread() IOError Close file'
                fileLock.release()
                config_file.close()
                pass
        #Remove record to file
        elif (self.Operation == "d"):
            try:
                working_file = self.FileName + '~'

                with open(self.FileName) as config_file, open(working_file, "w") as working:
                    try:
                        for line in config_file:
                            if self.Record not in line: # Delete the participant
                                working.write(line)
                        os.rename(working_file, self.FileName)
                    finally:
                        fileLock.release()
                        config_file.close()
                        working.close()
                        #print 'ReadWriteFileThread() Close file'
            except IOError:
                logging.exception('ReadWriteFileThread() IOError Close file')
                fileLock.release()
                config_file.close()
                working.close()
                pass
            except Exception,e:
                logging.exception(str(e))
                fileLock.release()
                config_file.close()
                working.close()
        else:
            print "ReadWriteFileThread() Invalid operation: " + str(self.Operation)
            fileLock.release()


###########################################################################################
# System configuration
###########################################################################################

def initializeSystem():
    systemMode = getSystemMode()
    initResult = readConferenceFileConfiguration()
    deleteFile(systemParticipantList)
    createParticipantsFile(systemParticipantList)
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
        print "XML-RPC Server initialized..."
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
    logging.info('getActiveCallsFromFile() total number of active calls  in file')


#############################################################################################

def insertActiveCallsToFile():
    logging.info('insertActiveCallsToFile() total number of active calls inserted to file: ' + str(len(callsGenerated)))
    for call in callsGenerated:
        call.insertCall()

#############################################################################################

def deleteParticipantFromFile(participantId):
    logging.info('deleteParticipantFromFile()')
    try:
        threadRead = ReadWriteFileThread("Thread-Delete", 3, systemParticipantList, "d",participantId)
        threadRead.start()
        threadRead.join()
        return True
    except Exception,e:
        logging.exception(str(e))
        return False

#############################################################################################

def deleteParticipantFromCache(participantId):
    global activeParticipantInformationCache
    logging.info('deleteParticipantFromCache() Active calls: [' + str(len(activeParticipantInformationCache)) + '] a call will be deleted: ' + participantId )
    for participant in activeParticipantInformationCache:
        call = processParticipantInformation(participant)
        print call['participantID']
        if call['participantID'] == participantId:
            activeParticipantInformationCache.remove(participant)
            logging.info('deleteParticipantFromCache() Participant deleted from cached: ' + participantId)
            logging.info('deleteParticipantFromCache() Active calls: [' + str(len(activeParticipantInformationCache)) + ']' )
            return True
    logging.error('deleteParticipantFromCache() Participant was not deleted from cached')
    return False

def deleteParticipantHelper(participantId):
    logging.info('deleteParticipantHelper()')
    if deleteParticipantFromFile(participantId) and deleteParticipantFromCache(participantId):
        return True
    else:
        return False

#############################################################################################

def callGenerator(maxCalls):
    global callsGenerated
    logging.info('callGenerator() emulating Calls: ' + maxCalls)
    maxCalls = convertStr(maxCalls)
    staticEndpoints = len(staticSUTEndpoints)

    if maxCalls > 0:
        logging.info('callGenerator() staticSUTEndpoints')
        if staticEndpoints>0:
            for staticEndpoint in staticSUTEndpoints:
                active = True
                participantId = generateNewParticipantId()
                conferenceId = getConferenceGUID()
                accessLevel = 'chair'
                displayName = 'endpoint-' + str(staticEndpoint)
                connectionState = 'connected'
                calls = "callID:" + participantId + " incoming: True address: " + str(staticEndpoint)
                addresses = "URI: " + str(staticEndpoint)
                logging.info('Creating call (' + str(staticEndpoint) + ')')
                newCall = Call(active,participantId, conferenceId, accessLevel, displayName, connectionState, calls,
                               addresses)
                # Insert new calls
                callsGenerated.append(newCall)
                logging.info('callGenerator() static call added into activeCalls. [' + str(len(callsGenerated)) + '] active calls now')

        logging.info('callGenerator() Creating calls...')
        for call in range(1, maxCalls + 1):
            #def __init__(self, participantId, active, conferenceId, accessLevel, displayName, connectionState, calls,addresses):
            #participantID,conferenceID,accessLevel,displayName,connectionState,calls,addresses
            #78eb3250-632f-11e4-b642-000d7c10b020,ab3798b0-4dbe-11e4-b63f-000d7c10b020,chair,ATT-Ops-SUT-1000,connected,{callID:'78eb0b40-632f-11e4-b642-000d7c10b020',incoming:True,address:'11111112130'},{URI:'9002'}
            active = True
            participantId = generateNewParticipantId()
            conferenceId = getConferenceGUID()
            accessLevel = 'chair'
            displayName = 'endpoint-' + str(call)
            connectionState = 'connected'
            calls = "callID:" + participantId + " incoming: True address: 1111111000" + str(call)
            addresses = "URI: 900" + str(call)
            logging.info('Creating call (' + str(call) + ')')
            newCall = Call(active,participantId, conferenceId, accessLevel, displayName, connectionState, calls,
                           addresses)
            # Insert new calls
            callsGenerated.append(newCall)
            participantMediaStatistics[participantId] = initializeMediaStatistics()

            logging.info('callGenerator() call added into activeCalls. [' + str(len(callsGenerated)) + '] active calls now')
    else:
        logging.error('callGenerator() Invalid number of calls configured')
        return -1

    mediaCalls = Process(target=initializeActiveCallsMediaStatistics(participantMediaStatistics,lock,counter))
    mediaCalls.start()
    mediaCalls.join()

    logging.info('callGenerator() Calls inserted: [' + str(len(callsGenerated)) + ']')

#############################################################################################

def initializeActiveCallsMediaStatistics(activeCalls,lock,c):

    try:
        print 'initializeActiveCallsMediaStatistics() : ' + str(len(activeCalls)) + ' active calls'

        while True:
            time.sleep(10.0)
            print 'initializeActiveCallsMediaStatistics() Processing calls media statistics...'
            with lock:
                for participant in activeCalls.keys():
                    print 'Increasing media statistics: ' + str(c.value)
                    #http://eli.thegreenplace.net/2012/01/04/shared-counter-with-pythons-multiprocessing
                c.value *= 1 + (1 + randint(1,5))

    except KeyboardInterrupt:
        print 'keepAliveController() Exiting...'
    except Exception, e:
        print 'keepAliveController() Exception' + str(e)


#############################################################################################

def getActiveCallsbyParticipantId(participantId):
    logging.info('getActiveCallsParticipantId() total number of active calls: ' + str(len(activeParticipantInformationCache)))
    for participant in activeParticipantInformationCache:
        call = processParticipantInformation(participant)
        if call['participantID'] == participantId:
            return True
    return False

#############################################################################################
# calls is a List of Dictionary, in this case ActiveParticpantInformationCache
# Verify each call and see if participant exist, if not return False

def checkIfParticipantIdExistInMemory(calls,participantID):
    for call in calls:
         if participantID in call:
             logging.info('checkIfParticipantIdExistInMemory() Participant already exists in cache')
             return True
    return False

#############################################################################################

def getConferenceGUID():
    return getSystemMode('conferenceGUID')

#############################################################################################

def getStaticSUTEndPoints():

    logging.info("Reading CTS1000 and CTS3000")
    print "getStaticSUTEndPoints() Obtaining CTS1000 and CTS3000 endpoint information..."
    global staticSUTEndpoints
    cts1000 = getSystemMode("cts1000")
    cts3000 = getSystemMode("cts3000")
    if cts1000:
        logging.info("CTS 1000 address is: " + str(cts1000))
        staticSUTEndpoints.append(cts1000)
    else:
        logging.warning("CTS 1000 address is not defined")

    if cts3000:
        logging.info("CTS 3000 address is: " + str(cts3000))
        staticSUTEndpoints.append(cts3000)
    else:
        logging.warning("CTS 3000 address is not defined")

    print "getStaticSUTEndPoints() Endpoint information: " + str(staticSUTEndpoints)

#############################################################################################

def startCallServer():
    logging.info("Starting call emulator services...")
    print "Starting call emulator services..."
    if getSystemMode("callControl") == 'True':
        logging.info('Call emulator started succesfully')
        print "Call emulator started succesfully."
        getStaticSUTEndPoints()
        callGenerator(getSystemMode("maxCalls"))
        insertActiveCallsToFile()
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

def updateParticipantInformation(active,participantID, conferenceID, accessLevel, displayName, connectionState,calls,addresses):
     if castRecordElement(participantID) == participantFieldDataType[1] and castRecordElement(conferenceID) == participantFieldDataType[2] and castRecordElement(displayName) == participantFieldDataType[4]:
        # TODO if participant already exists do not insert
        if not checkIfParticipantIdExistInMemory(activeParticipantInformationCache,participantID):
            activeParticipantInformationCache.append([participantID, conferenceID, accessLevel,displayName,connectionState,calls,addresses])
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

def createParticipantsFile(filename):
    try:
        logging.info("recreateParticipantsFile() Creating new file")
        file = open(filename, "w")
        file.write("active,participantID,conferenceID,accessLevel,displayName,connectionState,calls,addresses\n")
        file.close()
    except OSError,e:
        logging.error("recreateParticipantsFile() Exception found" + str(e))
        pass

#############################################################################################

def deleteFile(filename):
    try:
        os.remove(filename)
    except OSError,e:
        logging.error("recreateParticipantsFile() Exception found" + str(e))
        pass

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
    activeCallsInFileRecords = copy.copy(fileRecords)

    if len(activeCallsInFileRecords) < 1:
        return -1
    for call in activeCallsInFileRecords:
        logging.info("readActiveParticipants()" + str(call))
        paramNumber = 0
        if len(call) == 7:
            for field in call:
                paramNumber += 1
        else:
            logging.warning("readActiveParticipants() Invalid Record: " + call)
            return -1


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
                                active = field
                            if paramNumber == 1:
                                participantID = field
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

                    #Active field is just used for internal purposes
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
                 #Active field is just used for internal purposes
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
    threadRead.join()

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

################ Handle Feedback Reciever configuration ################

# Flex Mode methods
def feedbackReceiver_configure(msg):
    print("feedbackReceiver() API feedbackReceiver.configure")
    logInfo("feedbackReceiver() API feedbackReceiver.configure")
    params = xml_RequestHandler(msg)
    receiverURI = ''
    global feedBackServerList
    global feedBackServerListQueue

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
    print feedbackServerInstance

    """ Check Object does not exist in FeedBack receiver List"""

    if not feedBackServerList.has_key(receiverIndex):
        # Add shared access object
        feedBackServerListQueue.put(feedbackServerInstance)
        # Add feedbackServerInstance into List
        feedBackServerList[receiverIndex] = feedbackServerInstance
        logging.info('feedbackReceiver() feebackReceiver added ' + str(receiverIndex))
        print 'feedbackReceiver() feebackReceiver added ' + str(receiverIndex)

        # Ack feedBackReceiver
        feedbackServerInstance.getKeepAliveInstance().keepAlive('configureAck')
        feedbackServerInstance.getKeepAliveInstance().keepAlive('flexAlive')

        print 'feedbackReceiver() Current feedbackReceivers: ' + str(len(feedBackServerList))
        print 'feedbackReceiver() Current feedbackReceivers shared acess: ' + str(feedBackServerListQueue.__sizeof__())
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

################ Manage Feedback Receiver requests ################

def keepAliveController():
    #global feedBackServerListQueue
    print 'Initialize keepAliveController()'
    try:
        print 'keepAliveController() Init'
        print 'keepAliveController() Size: ' + str(feedBackServerListQueue.__sizeof__())

        while True:
            time.sleep(10.0)
            print 'keepAliveController() Processing feedbackReceivers...'
            feedBackServerElement = feedBackServerListQueue.get()
            if feedBackServerElement is None:
                print 'keepAliveController() Is empty'
                feedBackServerListQueue.task_done()
                break
            else:
                print 'keepAliveController() FeedBack receiver keepalive sent to: ' + str(feedBackServerElement)

            feedBackServerElement.getKeepAliveInstance().keepAlive('flexAlive')
            #Add back object so we can continue to process the KeepAlives
            feedBackServerListQueue.put(feedBackServerElement)

    except KeyboardInterrupt:
        print 'keepAliveController() Exiting...'
    except Exception, e:
        print 'keepAliveController() Exception' + str(e)

################ Generate random cookies ################

def getCookieValue():
    #Generate random string:
    return '265;0;' + random_string(3)


def getActiveParticipantList():
    try:
        logging.info("getActiveParticipantList() : " + systemParticipantList)
        participantsProcessed = []

        threadRead = ReadWriteFileThread("Thread-Read", 2, systemParticipantList, "r", "")
        threadRead.start()
        threadRead.join()

        if activeParticipantInformationCache:
            for participant in activeParticipantInformationCache:
                participantsProcessed.append(processParticipantInformation(participant))
        else:
            logging.error("getActiveParticipantList() No active participants obtained from cached")

        logging.info("getActiveParticipantList() Participants processed: " + str(len(participantsProcessed)))
        if len(participantsProcessed)>=1:
            #return Arr
            return participantsProcessed
        else:
            return None
    except Exception,e:
        print "Exception found" + str(e)
        logging.exception("Exception found " + str(e))

def processParticipantInformation(participant):
    """
    Process participant information from file, assuming participant is already processed
    :return:
        [{
      0  participantId: b3fk365k-3c33-xlce-sc8f-85yxb1kvx621,
      1  conferenceId: 8ca0c690-dd82-11e2-84f9-000d7c112b10,
      2  accessLevel: chair,
      3  displayName: endpoint-1,
      4  connectionState: connected,
      5  calls: [{callID: b3fk365k-3c33-xlce-sc8f-85yxb1kvx621, incoming: True, address: 11111110001}],
      6  addresses: [{URI: 9001}]
         }]

        [{'displayName': 'endpoint-1',
           'participantId': 'b3fk365k-3c33-xlce-sc8f-85yxb1kvx621',
           'calls': [{'callID': 'b3fk365k-3c33-xlce-sc8f-85yxb1kvx621',
            'incoming': True, 'address': '11111110001'}],
            'conferenceId': '8ca0c690-dd82-11e2-84f9-000d7c112b10',
            'connectionState': 'connected',
            'accessLevel': 'chair',
            'addresses': [{'URI': '9001'}]
        }]
    """

    regex = re.compile(r"\b(\w+)\s*:\s*([^:]*)(?=\s+\w+\s*:|$)")
    calls = []
    addresses = []
    participantProcessed = {}

    logging.info('processParticipantInformation()')
    logging.info('----------------------------------------------')
    #print "----------------------------------------------"
    #print "participantID: " + participant[0]
    #logging.info('processParticipantInformation participantID: ' + participant[0])
    #print "conferenceId: " + participant[1]
    #logging.info('conferenceId: ' + participant[1])

    #print "accessLevel: " + participant[2]
    #print "displayName: " + participant[3]
    #print "connectionState: " + participant[4]
    field = dict(regex.findall(participant[5]));
    field['incoming'] = True
    calls.append(field)
    #print "calls: " + str(field)
    field = dict(regex.findall(participant[6]));
    addresses.append(field)
    #print "addresses: " + str(field)

    participantProcessed['participantID'] = participant[0]
    participantProcessed['conferenceId']  = participant[1]
    participantProcessed['accessLevel']   = participant[2]
    participantProcessed['displayName']   = participant[3]
    participantProcessed['connectionState'] = participant[4]
    participantProcessed['calls'] = calls
    participantProcessed['addresses'] = addresses

    logging.info('processParticipantInformation() ' + str(participantProcessed['participantID']))
    #return Dict
    return participantProcessed

def flex_participant_enumerate(msg):
    print('flex_participant_enumerate() API flex.participant.enumerate')
    logInfo("flex_participant_enumerate() API flex.participant.enumerate")
    # Optional parameters:
    # cookie
    # max
    # conferenceID

    moreAvailable = False
    xmlResponse = []
    params = xml_RequestHandler(msg)

    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        participantsInfo = getActiveParticipantList()
        cookieValue = getCookieValue()

        if participantsInfo==None:
            return fault_code(systemErrors[5], 5)

        # Validate number of participants
        if len(participantsInfo) > 0 and len(participantsInfo) <=10:
            moreAvailable = False
        elif len(participantsInfo)>=10:
            participantsInfo[:10]
            moreAvailable = True
        else:
            return fault_code(systemErrors[201], 201)

        if (participantsInfo != None):
            xmlResponse = {'Cookie': cookieValue, 'moreAvailable': moreAvailable, 'participants': participantsInfo}
            return xmlResponse
        else:
            return fault_code(systemErrors[201], 201)

def flex_participant_setMute(msg):
    print "flex_participant_setMute() API flex.participant.setMute"
    logInfo("flex_participant_setMute() API flex.participant.setMute")
    # Optional parameters:
    # audioRxMute
    # videoRxMute
    # audioTxMute
    # audioTxMute
    # Mandatory
    # participantId
    params = xml_RequestHandler(msg)
    xmlResponse = []
    participantFound = False

    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        # Verify authentication and then collect other parameters
        for element in params:
            if element == 'participantID':
                logging.info('participantId param found')
                participantReq = params.get('participantID')
                if getActiveCallsbyParticipantId(participantReq):
                    logging.info('participantId is active')
                    participantFound = True
            if element == 'audioRxMute':
                logging.info('audioRxMute param found')
            if element == 'videoRxMute':
                logging.info('videoRxMute param found')
            if element == 'audioTxMute':
                logging.info('audioTxMute param found')
            if element == 'audioTxMute':
                logging.info('audioTxMute param found')

        if (participantFound):
            xmlResponse = {'status': 'operation succesful'}
            return xmlResponse
        else:
            logging.error('flex_participant_setMute() participantID not found')
            return fault_code(systemErrors[5], 5)

def flex_participant_sendUserMessage(msg):
    print "flex_participant_sendUserMessage() API flex.participant.sendUserMessage"
    logInfo("flex_participant_sendUserMessage() API flex.participant.sendUserMessage")
    # Optional parameters:

    # Mandatory
    # participantId
    params = xml_RequestHandler(msg)
    xmlResponse = []
    participantFound = False


    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        # Verify authentication and then collect other parameters
        for element in params:
            if element == 'participantID':
                logging.info('participantId param found')
                participantReq = params.get('participantID')
                if getActiveCallsbyParticipantId(participantReq):
                    logging.info('participantId is active')
                    participantFound = True
            if element == 'message':
                logging.info('message param found')
                message = params.get('message')
                logging.info('flex_participant_sendUserMessage() message: ' + message)
                print 'flex_participant_sendUserMessage(): ' + message

        if (participantFound):
            xmlResponse = {'status': 'operation succesful'}
            return xmlResponse
        else:
            logging.error('flex_participant_sendUserMessage() participantID not found')
            return fault_code(systemErrors[5], 5)

def flex_participant_destroy(msg):
    print "flex_participant_destroy() API flex.participant.destroy"
    logInfo("flex_participant_destroy() API flex.participant.destroy")
    # Optional parameters:

    # Mandatory
    # participantId
    params = xml_RequestHandler(msg)
    xmlResponse = []
    participantFound = False


    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        # Verify authentication and then collect other parameters
        for element in params:
            if element == 'participantID':
                logging.info('participantId param found')
                participantReq = params.get('participantID')
                if deleteParticipantHelper(participantReq):
                    logging.info('participantId is active will be terminated')
                    participantFound = True
                else:
                    logging.error('Error deleting participant')

        if (participantFound):
            xmlResponse = {'status': 'operation succesful'}
            return xmlResponse
        else:
            logging.error('flex_participant_destroy() participantID not found')
            return fault_code(systemErrors[5], 5)

def flex_participant_modify(msg):
    print "flex_participant_modify() API flex.participant.modify"
    logInfo("flex_participant_modify() API flex.participant.modify")
    # Optional parameters:

    # Mandatory
    # participantId
    params = xml_RequestHandler(msg)
    xmlResponse = []
    participantFound = False

    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        # Verify authentication and then collect other parameters
        for element in params:
            if element == 'participantID':
                logging.info('participantId param found')
                participantReq = params.get('participantID')
                if getActiveCallsbyParticipantId(participantReq):
                    logging.info('participantId is active')
                    participantFound = True
        if (participantFound):
            xmlResponse = {'status': 'operation succesful'}
            return xmlResponse
        else:
            logging.error('flex_participant_modify() participantID not found')
            return fault_code(systemErrors[5], 5)

def flex_participant_requestDiagnostics(msg):
    print "flex_participant_requestDiagnostics() API flex.participant.requestDiagnostics"
    logInfo("flex_participant_requestDiagnostics() API flex.participant.requestDiagnostics")
    # Optional parameters:

    # Mandatory
    # participantId
    params = xml_RequestHandler(msg)
    xmlResponse = []
    participantFound = False

    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        # Verify authentication and then collect other parameters
        for element in params:
            if element == 'participantID':
                logging.info('participantId param found')
                participantReq = params.get('participantID')
                if getActiveCallsbyParticipantId(participantReq):
                    logging.info('participantId is active')
                    participantFound = True
                    processParticipantDiagnosticResponse(participantReq)
        if (participantFound):
            xmlResponse = {'status': 'operation succesful'}
            return xmlResponse
        else:
            logging.error('flex_participant_modify() participantID not found')
            return fault_code(systemErrors[5], 5)


################ Respond to ParticipantDiagnosticRequest ################

def notifyFeedBackReceiverClients(participantId):
    global feedBackServerList
    logging.info('notifyFeedBackReceiverClients() elements: ' + str(len(feedBackServerList)))
    for feedBackServer in feedBackServerList.itervalues():
        print "notifyFeedBackReceiverClients(): " + str(feedBackServer.uri)
        if feedBackServer.uri:
            notifier = Process(target=participantDiagnosticResponseNotifier(feedBackServer.uri,participantId))
            notifier.start()
            notifier.join()
        else:
            logging.error('notifyFeedBackReceiverClients() Invalid Uri')

################ Respond to ParticipantDiagnosticRequest ################

def processParticipantDiagnosticResponse(participantId):

    if getSystemMode("emulatePacketLoss") == 'True':
        logging.info('processParticipantDiagnosticResponse() Packet loss will be emulated for each method call')
        if getActiveCallsbyParticipantId(participantId):
                    logging.info('participantId is active')
                    participantFound = True
                    # Now we send to Feedback Receiver port
                    notifyFeedBackReceiverClients(participantId)
        else:
            logging.warning('processParticipantDiagnosticResponse() Participant not found')
            return -1
    else:
        logging.info('processParticipantDiagnosticResponse() Packet loss is not active')

# initializeMediaStatistics

def initializeMediaStatistics():

    # Media Arrays
    audioRx = []
    audioTx = []
    videoRx = []
    videoTx = []

    # AuxiliaryAudioRx/Tx VideoRx/Tx
    auxiliaryAudioRx = []
    auxiliaryAudioTx = []
    contentVideoRx   = []
    contentVideoTx   = []

    # Contents of Structure
    audioRxStruct = {}
    audioTxStruct = {}
    videoRxStruct = {}
    videoTxStruct = {}
    auxiliaryAudioRxStruct = {}
    auxiliaryAudioTxStruct = {}
    contentVideoTxStruct   = {}
    contentVideoRxStruct   = {}

    # We will populate and increase value for each call. Initial values are stored in a Queue, additional values are added
    # for each call
    audioRxStruct['codec'] = 'AAC-LD'
    audioRxStruct['encrypted'] = True
    audioRxStruct['channelBitRate'] = 64000
    audioRxStruct['jitter'] = 4
    audioRxStruct['energy'] = -25
    audioRxStruct['packetsReceived'] = 11400
    audioRxStruct['packetErrors'] = 0
    audioRxStruct['packetsMissing'] = 0
    audioRxStruct['framesReceived'] = 11000
    audioRxStruct['frameErrors'] = 0
    audioRxStruct['muted'] = True
    audioRxStruct['clearPathOverhead'] = 0
    audioRxStruct['clearPathRecovered'] = 0

    audioTxStruct['codec'] = 'AAC-LD'
    audioTxStruct['encrypted'] = True
    audioTxStruct['channelBitRate'] = 64000
    audioTxStruct['packetsSent'] = 11400
    audioTxStruct['packetsLost'] = 0
    audioTxStruct['muted'] = False
    audioTxStruct['clearPathOverhead'] = 0
    audioTxStruct['clearPathRecovered'] = 0

    videoRxStruct['codec'] = 'H.264'
    videoRxStruct['height'] = 288
    videoRxStruct['width'] = 352
    videoRxStruct['encrypted'] = True
    videoRxStruct['channelBitRate'] = 4000000
    videoRxStruct['expectedBitRate'] = 4000000
    videoRxStruct['expectedBitRateReason'] = "notLimited"
    videoRxStruct['actualBitRate'] = 143892
    videoRxStruct['jitter'] = 50
    videoRxStruct['packetsReceived'] = 2863
    videoRxStruct['packetErrors'] = 6
    videoRxStruct['framesReceived'] = 1069
    videoRxStruct['frameErrors'] = 2
    videoRxStruct['frameRate'] = 8
    videoRxStruct['fastUpdateRequestsSent'] = 1
    videoRxStruct['muted'] = False
    videoRxStruct['clearPathOverhead'] = 0
    videoRxStruct['clearPathRecovered'] = 0

    videoTxStruct['codec'] = 'H.264'
    videoTxStruct['height'] = 720
    videoTxStruct['width'] = 1280
    videoTxStruct['encrypted'] = True
    videoTxStruct['channelBitRate'] = 448000
    videoTxStruct['configuredBitRate'] = 432000
    videoTxStruct['configuredBitRateReason'] = 'aggregateBandwidth'
    videoTxStruct['actualBitRate'] = 356985
    videoTxStruct['packetsSent'] = 5646
    videoTxStruct['frameRate'] = 30
    videoTxStruct['fastUpdateRequestsReceived'] = 0
    videoTxStruct['muted'] = False
    videoTxStruct['packetsLost'] = 4
    videoTxStruct['clearPathOverhead'] = 0
    videoTxStruct['clearPathRecovered'] = 1
    videoTxStruct['clearPathLTRF'] = True

    contentVideoRxStruct['codec'] = 'H.263+'
    contentVideoRxStruct['height'] = 0
    contentVideoRxStruct['width'] = 0
    contentVideoRxStruct['encrypted'] = False
    contentVideoRxStruct['channelBitRate'] = 768000
    contentVideoRxStruct['expectedBitRate'] = 768000
    contentVideoRxStruct['expectedBitRateReason'] = 'notLimited'
    contentVideoRxStruct['actualBitRate'] = 0
    contentVideoRxStruct['jitter'] = 0
    contentVideoRxStruct['packetsReceived'] = 0
    contentVideoRxStruct['packetErrors'] = 0
    contentVideoRxStruct['framesReceived'] = 0
    contentVideoRxStruct['frameErrors'] = 0
    contentVideoRxStruct['frameRate'] = 0
    contentVideoRxStruct['fastUpdateRequestsSent'] = 0

    # Assign references
    audioRx.append(audioRxStruct)
    audioTx.append(audioTxStruct)
    videoRx.append(videoRxStruct)
    videoTx.append(videoTxStruct)
    auxiliaryAudioRx.append(auxiliaryAudioRxStruct)
    auxiliaryAudioTx.append(auxiliaryAudioTxStruct)
    contentVideoRx.append(contentVideoRxStruct)
    contentVideoTx.append(contentVideoTxStruct)

    return 0

# Send notification to Feedback Receiver after participant diagnostic request
def participantDiagnosticResponseNotifier(url,participantId):
    parameters = {'participantID': participantId, 'sourceIdentifier': participantId}
    params = tuple([parameters])
    xmlrpccall = xmlrpclib.dumps(params,'participantDiagnosticResponse',encoding='UTF-8')
    response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100,
                             stream = False, )
    if response.status_code == 200:
        result = xmlrpclib.loads( response.content, )[ 0 ]
        print result
    else:
  	    print '(participantDiagnosticResponse) Error'
  	    return -1

# Register an instance; all the methods of the instance are published as XML-RPC methods (in this case, just 'div').
class Methods:
    def show_version(self):
        print("show_version() API show.version")
        logInfo("show_version() API show.version")
        return version

# Create server
server = SimpleXMLRPCServer((hostname, port), requestHandler=XmlRequestHandler, logRequests=True)
server.register_function(ping_function, 'ping')
# flexmode
server.register_function(feedbackReceiver_configure, 'feedbackReceiver.configure')
server.register_function(flex_participant_enumerate, 'flex.participant.enumerate')
server.register_function(flex_participant_setMute, 'flex.participant.setMute')
server.register_function(flex_participant_sendUserMessage, 'flex.participant.sendUserMessage')
server.register_function(flex_participant_destroy, 'flex.participant.destroy')
server.register_function(flex_participant_modify, 'flex.participant.modify')
server.register_function(flex_participant_requestDiagnostics, 'flex.participant.requestDiagnostics')
server.register_instance(Methods())

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

# Main function
def telepresenceServer():
    logging.basicConfig(filename='logs/telepresence.log', level=logging.INFO,
                        format='%(asctime)s.%(msecs).03d %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.info("-----------------------Initializing server------------------------")
    print "-----------------------Initializing server------------------------"
    try:
        """initialize system"""
        initializeSystem()
        feedbackReceiverInitialize()

        xml = Process(target=startXmlRpc)
        cc = Process(target=startCallServer)
        keepaliveInit = Process(target=keepAliveController)

        """Start xmlServer and callServer"""
        xml.start()
        cc.start()
        keepaliveInit.start()

        xml.join()
        cc.join()
        keepaliveInit.join()

    except KeyboardInterrupt:
        print "Cisco TelePresence Server 8710 Emulator stopping...."
        logging.info("Cisco TelePresence Server 8710 Emulator stopping....")
    except Exception, e:
        print "Exception found" + str(e)
        logging.exception("Exception found " + str(e))



if __name__ == '__main__':

    telepresenceServer()