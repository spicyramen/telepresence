'''
@author Gonzalo Gasca Meza
		AT&T Labs 
		Date: June 2013
		Emulates TelePresence Server 8710 Server API
'''
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from os import urandom
from random import randrange
from itertools import islice, imap, repeat
from types import *
import time
import string
import xmlrpclib
import csv
import threading
import thread
import logging
import copy

hostname = "localhost"
port     = 8080
version  = '2.3(1.48)'
configurationFile = 'configuration.xml'
systemFile = 'system.xml'
systemUserName = "sut"
systemPassWord = "1qaz2wsx"

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
	'conferenceName',]

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
	21: 'conferenceName'}

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
	101:'Missing parameter',
	102:'Invalid parameter',
	103:'Malformed parameter',
	105:'Request too large',
	201:'Operation failed',
	202:'Product needs its activation feature key',
	203:'Too many asynchronous requests'
}

dataType =  [
	IntType,  		# 0  - portsContentFree
    BooleanType, 	# 1  - locked
    IntType,  		# 2  - oneTableMode
    IntType,  		# 3  - portsAudioFree
    BooleanType, 	# 4  - roundTableEnable
    IntType,  		# 5  - videoPortLimit
    IntType,  		# 6  - conferenceID
    BooleanType, 	# 7  - persistent
    IntType,  		# 8  - portsVideoFree
    IntType,  		# 9  - audioPortLimit
    StringType,  	# 10 - conferenceGUID
    BooleanType, 	# 11 - audioPortLimitSet
    IntType,  		# 12 - pin
    BooleanType, 	# 13 - active
    BooleanType, 	# 14 - videoPortLimitSet
    BooleanType, 	# 15 - registerWithGatekeeper
    IntType,  		# 16 - numericID
    ListType,   	# 17 - participantList
    BooleanType, 	# 18 - recording
    BooleanType, 	# 19 - registerWithSipRegiStringTypear
    IntType,  		# 20 - h239ContributionID
    StringType,		# 21 - conferenceName
]

systemConfigurationDb = [
]

FILECONFIGURATION_LOCK = threading.Lock()

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
		except: # This should only happen if the module is buggy
			# internal error, report as HTTP server error
			self.send_response(500)
			self.end_headers()
			loggin.error('Internal error')
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

class ReadWriteFileThread(threading.Thread):
	def __init__(self, threadID, FileName,Operation):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.FileName = FileName
        self.Operation = Operation
    def run(self):
            FILECONFIGURATION_LOCK.acquire()
            try:
				with open(configurationFile,"r") as config_file:
					try:
						fileRecords = csv.reader(config_file, delimiter=',',skipinitialspace=True)
						allRecords = [record for record in fileRecords]
					finally:
						config_file.close();
						if validateData(allRecords) == -1:
							return -2		
			except IOError: 
				pass       
            FILECONFIGURATION_LOCK.release()
  

###########################################################################################
# System configuration
###########################################################################################

def _init_():

	init = readConfigurationFile()
	if init == -1:
		print "Error invalid configuration"
		logging.error("_init_() Error invalid configuration")
		print "Program exiting...."
		logging.error("_init_() Program exiting....")	
		raise SystemExit
	elif init == -2:
		print "Error invalid records detected"
		logging.error("_init_() Error invalid records detected")
		print "Program exiting...."
		logging.error("_init_() Program exiting....")	
		raise SystemExit
	else:
		return	
	
# Run the server's main loop
def startXmlRpc():

	logging.info("Cisco TelePresence Server 8710 Emulator started....")
	print "Cisco TelePresence Server 8710 Emulator started...."
	logging.info("Hostname: " + hostname +  " Port: " + str(port))
	print "Hostname: " + hostname +  " Port: " + str(port)
	logging.info("API Version:  " + version)
	print "API Version:  " + version
	try:		
		logging.info("XML-RPC Server initialized...")
		threading.Thread(target=server.serve_forever()).start()
	except KeyboardInterrupt:
		print ""
		logging.info("Cisco TelePresence Server 8710 Emulator stopping....")
	except Exception as instance:
		print type(inst)
		print inst.args
		logging.error("startXmlRpc() Exception: " + str(instance))
		raise SystemExit


# Verify configuration file
def readConfigurationFile():
	logging.info("Reading system configuration file: " + configurationFile)
	try:
		with open(configurationFile,"r") as config_file:
			try:
				fileRecords = csv.reader(config_file, delimiter=',',skipinitialspace=True)
				allRecords = [record for record in fileRecords]
			finally:
				config_file.close();
				if validateConfiguration(allRecords) == -1:
					return -1
				if validateData(allRecords) == -1:
					return -2		
	except IOError: 
		pass


def updateSystemConfiguration(conferenceID,conferenceGUID,numericID):
	#Stores information from XML file
	#conferenceID,conferenceGUID,numericID
	if castRecordElement(conferenceID) == dataType[6] and castRecordElement(conferenceGUID) == dataType[10] and castRecordElement(numericID) == dataType[16]: 
		systemConfigurationDb.append({int(conferenceID),conferenceGUID,int(numericID)})
		logging.info("updateSystemConfiguration() Valid record " +  conferenceID + " " + conferenceGUID + " "  + numericID)
		return True
	else:
		logging.error("updateSystemConfiguration() Invalid record " +  conferenceID + " " + conferenceGUID + " "  + numericID)
		return False  

# Verify configuration parameters in file
def validateConfiguration(fileparams):
	for param in fileparams[0]:
		if param in configParameters:
			logging.info('validateConfiguration() Valid parameter: ' + param)
		else:
			logging.info('validateConfiguration() Invalid parameter: ' + param)
			return -1

#Verify password is correct
def authenticationModule(username,password):
	if len(username)>128 or len(password)>128:
		return False
	if username == systemUserName and password == systemPassWord:
		return True
	else:
		return False

# Return number of lines in file
def readFileLines(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

# Verify records in file
def validateData(fileRecords):
	logging.info("Validating system configuration data...")
	#file_lines(configurationFile)
	logging.info("validateData() Processing " + str(readFileLines(configurationFile) -1 ) + " record(s)...")
	# Delete first line
	del fileRecords[0]
	# Copy fileRecords to global systemRecords
	global systemRecords
	systemRecords = copy.copy(fileRecords)
	if len(fileRecords)<1:
		return -1
	for record in fileRecords:
		logging.info("validateData() " + str(record))
		paramNumber = 0
		if len(record) == 22:
			for field in record:
				if paramNumber == 12 and field == "''": # No PIN					
					paramNumber += 1			
				elif castRecordElement(field) == dataType[paramNumber]:							
					if paramNumber == 6:
						conferenceID = field
					if paramNumber == 10:
						conferenceGUID = field
					if paramNumber == 16:
						numericID = field
					paramNumber += 1						
    			else:
    				if paramNumber!=22:
	    				logging.info("validateData() Invalid data paramNumber: " + str(paramNumber))
    					return -1
    			updateSystemConfiguration(conferenceID,conferenceGUID,numericID)
		else:
			logging.warning("validateData() Invalid record: " + record)
			return -1	


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
	if (authenticationModule(username,password)):
		del params['authenticationUser']
		del params['authenticationPassword']
		return params
	else:
		return 34			

#Read file and update systemConfigurationDb
def updateConfigurationInfo(string,sleeptime,*args):
	print "updateConfigurationInfo() Updating cache...."
	logging.info("updateConfigurationInfo: " + configurationFile)
	try:
		with open(configurationFile,"r") as config_file:
			try:
				fileRecords = csv.reader(config_file, delimiter=',',skipinitialspace=True)
				allRecords = [record for record in fileRecords]
			finally:
				config_file.close();
				if validateData(allRecords) == -1:
					return -1		
	except IOError: 
		pass


#Find param X in conference record
def findParameterInConference(param):
	if param >= 0 and param < len(conferenceParameters):
		return conferenceParameters[param]
	else:
		return -1

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
	if conferenceName.find("'")==-1:
		conferenceName = "'" + conferenceName + "'"

	if len(conferenceName)>80 and not isinstance(conferenceName, str):
  		return -1

  	logging.info("createConferenceByConferenceName() Creating new conference...")
	conferenceID   = generateNewConferenceID()
	conferenceGUID = generateNewConferenceGUID()
	numericID	   = generateNewNumericID()
	logging.info("createConferenceByConferenceName() New conferenceID: " + str(conferenceID))
	logging.info("createConferenceByConferenceName() New conferenceGUID: " + str(conferenceGUID))
	logging.info("createConferenceByConferenceName() New numericID: " + str(numericID))

	if len(conferenceGUID)!=36 and not isinstance(conferenceGUID, str):
  		return -1

  	while(not validnewRecord and attempts<maxAttempts):
	  	if conferenceID > 10000 or numericID > 10000:
			return -1
			break
  		resultValidation = validateNewRecord(conferenceID,conferenceGUID,numericID)
		if resultValidation == -1:
			validnewRecord = False
			return -1
		elif resultValidation == -2:
			conferenceID   = generateNewConferenceID()
			attempts += 1
		elif resultValidation == -3:	
			numericID	   = generateNewNumericID()
			attempts += 1
		else:
		   validnewRecord = True
		   break

	if attempts>=maxAttempts:
		return -1

	try:
		# Add new record to Configuration file
		with open(configurationFile,"a") as config_file:
			try:
				newRecord = "24,False,0,10,False,0," + str(conferenceID) + ",True,24,0," + "'" + conferenceGUID + "'" +  ",False,'',True,False,True," + str(numericID) + ",[],False,True,0," + conferenceName
				config_file.write(newRecord + "\n")
				xmlResponse.append(conferenceGUID)
				xmlResponse.append(numericID)
				systemConfigurationDb.append({conferenceID,conferenceGUID,numericID})
				return xmlResponse
			finally:
				config_file.close();	
	except IOError: 
		pass


#Find conference record based on conferenceGUID
def findRecordByConferenceGUID(msg):
	print msg
	params = copy.deepcopy(msg)
	conferenceGUID = ''
	# Verify authentication and then collect other parameters
	for element in params:
		if element == 'conferenceGUID':
			conferenceGUID = params.get('conferenceGUID')		
		
	# 	Verify conferenceGUID status
	#   logging.info("findRecordByConferenceGUID: " + conferenceGUID)
	#   Add '' to conferenceGUID in case is not coming like that
	if conferenceGUID.find("'")==-1:
		conferenceGUID = "'" + conferenceGUID + "'"

	if len(conferenceGUID)!=36 and not isinstance(conferenceGUID, str):
  		return -1
  	else:
  		if len(systemRecords)<1:
			return -1
		else:
			for record in systemRecords:
				paramNumber = 0				
				for field in record:
					if paramNumber == 10:
						if field == conferenceGUID:
							print record
							return record
					else:
						paramNumber += 1									
	return -1	

# Generate random conference ID
def generateNewConferenceGUID():
	return random_string(8) + "-" + random_string(4) + "-" + random_string(4) + "-" + random_string(4) + "-" +  random_string(12)

# Generate random conferenceID
def generateNewConferenceID():
	return randrange(1000,9999)
# Generate random numeric ID
def generateNewNumericID():
	return randrange(1000,9999)

def validateNewRecord(conferenceID,conferenceGUID,numericID):
	for element in systemConfigurationDb:
		for item in element:
			if conferenceGUID == item:
				return -1
			if conferenceID == item:
				return -2
			if numericID == item:
				return -3
	return 0

# System UTILS

# Generate random String
def random_string(length):
    chars = set(string.ascii_lowercase + string.digits)
    char_gen = (c for c in imap(urandom, repeat(1)) if c in chars)
    return ''.join(islice(char_gen, None, length))

# Log info
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
        dp = dict( (i, estimateTypedValue(j)) for (i,j) in d.items())
        return dFxn(*cp, **dp)
    return wrapped


@autocast
def castRecordElement(element):
	if element == "[]":
		return  ListType
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
		return fault_code(systemErrors[34],34)
	elif(params == 101):
		return fault_code(systemErrors[101],101)
	else:
	  	xmlResponse = createConferenceByConferenceName(params)
	  	if (xmlResponse !=-1 and len(xmlResponse) >= 2):
	  		print "conference_create() API conference.create conferenceGUID:" + xmlResponse[0]
	  		logInfo(xmlResponse)
	  		xmlResponse = {'conferenceGUID' :xmlResponse[0],'numericID':xmlResponse[1]}
			return xmlResponse
	  	else:
	  		return fault_code(systemErrors[201],201)

def conference_delete(msg):
	return msg

def conference_enumerate(msg):
	# 	Optional params could be: 	
	#					enumerateID  integer
	#					activeFilter boolean
	#	conferenceName,conferenceID,conferenceGUID,active,persistent,locked,numericID,registerWithGatekeeper,registerWithSIPRegistrar,h239ContributionEnabled,pin
	logInfo("conference_enumerate() API conference.enumerate")
	xmlResponse = {'conferenceName' :'AT&T TelePresence Solution connection test','conferenceID':45966,'conferenceGUID':'6b30aed0-be06-11e2-af9d-000d7c112b10','active':True,'persistent':False,'locked':False,
	'numericID':8100,'registerWithGatekeeper':False,'registerWithSIPRegistrar':False,'h239ContributionEnabled':False,'pin':''}
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
		return fault_code(systemErrors[34],34)
	elif(params == 101):
		return fault_code(systemErrors[101],101)
	else:
	  	xmlResponse = findRecordByConferenceGUID(params)
	  	if (xmlResponse!=-1):
	  		logInfo(xmlResponse)
			return xmlResponse
	  	else:
	  		return fault_code(systemErrors[4],4)

def conference_uninvite(msg):
	return msg

def fault_code(string,code):
    	xmlResponse = {'faultCode' :code,'faultString':string }
    	logInfo(xmlResponse)
	return xmlResponse


# Register an instance; all the methods of the instance are published as XML-RPC methods (in this case, just 'div').
class Methods:
		def show_version(self):
			print("show_version() API show.version")
			logInfo("show_version() API show.version")
			return version

# Create server
server = SimpleXMLRPCServer((hostname, port),requestHandler=XmlRequestHandler,logRequests=True)
server.register_function(ping_function, 'ping')
server.register_function(conference_create, 'conference.create')
server.register_function(conference_delete, 'conference.delete')
server.register_function(conference_enumerate, 'conference.enumerate')
server.register_function(conference_invite, 'conference.invite')
server.register_function(conference_senddtmf, 'conference.senddtmf')
server.register_function(conference_sendmessage, 'conference.sendmessage')
server.register_function(conference_sendwarning, 'conference.sendwarning')
server.register_function(conference_set, 'conference.set')
server.register_function(conference_status, 'conference.status')
server.register_function(conference_uninvite, 'conference.uninvite')
server.register_instance(Methods())

# Main function
def main():
	logging.basicConfig(filename='tpsServer.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')	
	logging.info("-----------------------Initializing server------------------------")
	print "-----------------------Initializing server------------------------"
	try:
		_init_()
		startXmlRpc()
	except KeyboardInterrupt:
		logging.info ("Cisco TelePresence Server 8710 Emulator stopping....")
	except Exception,e:
		logging.error("Exception found " + str(e))

if __name__ == '__main__':
    main()
