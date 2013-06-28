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
import string
import xmlrpclib
import csv
import threading
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
	'h239ContributionID']

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
	20: 'h239ContributionID'}

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
]

#Stores information from XML file
#conferenceID,conferenceGUID,numericID
systemConfigurationDb = [
{1000,'8ca0c690-dd82-11e2-84f9-000d7c112b10',8100},
{1001,'8ca0c690-dd82-11e2-84f9-000d7c112b11',8101},
{1002,'8ca0c690-dd82-11e2-84f9-000d7c112b12',8102},
{1003,'8ca0c690-dd82-11e2-84f9-000d7c112b13',8103},
{1004,'8ca0c690-dd82-11e2-84f9-000d7c112b14',8104},
{1005,'8ca0c690-dd82-11e2-84f9-000d7c112b15',8105},
{1006,'8ca0c690-dd82-11e2-84f9-000d7c112b16',8106},
{1007,'8ca0c690-dd82-11e2-84f9-000d7c112b17',8107},
{1008,'8ca0c690-dd82-11e2-84f9-000d7c112b18',8108},
{1009,'8ca0c690-dd82-11e2-84f9-000d7c112b19',8109},
{1010,'8ca0c690-dd82-11e2-84f9-000d7c112b20',8110},
{1011,'8ca0c690-dd82-11e2-84f9-000d7c112b21',8111},
]

# Restrict to a particular path.

class XmlRequestHandler(SimpleXMLRPCRequestHandler):
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
# System configuration
###########################################################################################

def _init_():
	if read_configuration() == -1:
		print "Error invalid configuration"
		logging.error("Error invalid configuration")
		print "Program exiting...."
		logging.error("Program exiting....")	
		raise SystemExit

# Run the server's main loop
def startXmlRpc():

	logging.info("Cisco TelePresence Server 8710 Emulator started....")
	print "Cisco TelePresence Server 8710 Emulator started...."
	logging.info("Hostname: " + hostname +  " Port: " + str(port))
	print "Hostname: " + hostname +  " Port: " + str(port)
	logging.info("Version:  " + version)
	print "Version:  " + version
	try:		
		logging.info("XML-RPC Server initialized...")
		threading.Thread(target=server.serve_forever()).start()
	except KeyboardInterrupt:
		print ""
		logging.info("Cisco TelePresence Server 8710 Emulator stopping....")
	except Exception as instance:
		print type(inst)
		print inst.args
		logging.error("Exception: " + str(instance))


# Verify configuration file
def read_configuration():
	logging.info("Reading system configuration...")
	try:
		with open(configurationFile,"r") as config_file:
			try:
				fileRecords = csv.reader(config_file, delimiter=',',skipinitialspace=True)
				allRecords = [record for record in fileRecords]
			finally:
				config_file.close();
				if validate_config(allRecords) == -1:
					return -1
				if validate_data(allRecords) == -1:
					return -1		
	except IOError: 
		pass

# Verify configuration parameters in file
def validate_config(fileparams):
	for param in fileparams[0]:
		if param in configParameters:
			logging.info('validate_config() Valid param: ' + param)
		else:
			logging.info('validate_config() Invalid param: ' + param)
			return -1

#Verify password is correct
def authentication(username,password):

	if len(username)>128 or len(password)>128:
		return False
	if username == systemUserName and password == systemPassWord:
		return True
	else:
		return False

# Return number of lines in file
def file_lines(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

# Verify records in file
def validate_data(fileRecords):
	logging.info("Validating system configuration data...")
	#file_lines(configurationFile)
	logging.info("validate_data() Processing " + str(file_lines(configurationFile) -1 ) + " record(s)...")
	# Delete first line
	del fileRecords[0]
	# Copy fileRecords to global systemRecords
	global systemRecords
	systemRecords = copy.copy(fileRecords)
	if len(fileRecords)<1:
		return -1
	for record in fileRecords:
		logging.info(record)
		paramNumber = 0
		if len(record) == 21:
			for field in record:
				if paramNumber == 12 and field == "''": # No PIN					
					paramNumber += 1			
				elif castRecordElement(field) == dataType[paramNumber]:					
					paramNumber += 1    						
    			else:
    				if paramNumber!=21:
	    				logging.info("validate_data() Invalid data paramNumber: " + str(paramNumber))
    					return -1
		else:
			logging.warning("Invalid record " + record)
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
		return 101		
	if (authentication(username,password)):
		del params['authenticationUser']
		del params['authenticationPassword']
		return params
	else:
		return 34			

#Find param X in conference record
def find_paramin_conference(param):
	if param >= 0 and param < len(conferenceParameters):
		return conferenceParameters[param]
	else:
		return -1

#Create conference record based on create_recordby_conferenceName
def create_recordby_conferenceName(msg):
	maxAttempts = 50
	attempts = 0
	validnewRecord = False

	print msg
	params = copy.deepcopy(msg)
	conferenceName = ''
	# Verify authentication and then collect other parameters
	for element in params:
		if element == 'conferenceName':
			conferenceName = params.get('conferenceName')		
		
	# 	Verify conferenceGUID status
	logging.info("create_recordby_conferenceName: " + conferenceName)
	#   Add '' to conferenceGUID in case is not coming like that
	if conferenceName.find("'")==-1:
		conferenceName = "'" + conferenceName + "'"

	if len(conferenceName)>80 and not isinstance(conferenceName, str):
  		return -1

  	logging.info("Creating new conference...")
	conferenceID   = generate_conferenceID()
	conferenceGUID = generate_conferenceGUID()
	numericID	   = generate_numericID()
	logging.info(conferenceID)
	logging.info(conferenceGUID)
	logging.info(numericID)

	if len(conferenceGUID)!=36 and not isinstance(conferenceGUID, str):
  		return -1

  	while(not validnewRecord and attempts<maxAttempts):
	  	if conferenceID > 10000 or numericID > 10000:
			return -1
			break
  		resultValidation = validate_newRecord(conferenceID,conferenceGUID,numericID)
		if resultValidation == -1:
			validnewRecord = False
			return -1
		elif resultValidation == -2:
			conferenceID   = generate_conferenceID()
			attempts += 1
		elif resultValidation == -3:	
			numericID	   = generate_numericID()
			attempts += 1
		else:
		   validnewRecord = True
		   break

	if attempts>=maxAttempts:
		return -1

	try:
		with open(configurationFile,"a") as config_file:
			try:
				newRecord = "24,False,0,10,False,0," + str(conferenceID) + ",True,24,0," + "'" + conferenceGUID + "'" +  ",False,'',True,False,True," + str(numericID) + ",[],False,True,0"
				config_file.write(newRecord + "\n")
				xmlResponse = conferenceGUID
				systemConfigurationDb.append({conferenceID,conferenceGUID,numericID})
				return xmlResponse
			finally:
				config_file.close();	
	except IOError: 
		pass


#Find conference record based on conferenceGUID
def find_recordby_conferenceGUID(msg):
	print msg
	params = copy.deepcopy(msg)
	conferenceGUID = ''
	# Verify authentication and then collect other parameters
	for element in params:
		if element == 'conferenceGUID':
			conferenceGUID = params.get('conferenceGUID')		
		
	# 	Verify conferenceGUID status
	#   logging.info("find_recordby_conferenceGUID: " + conferenceGUID)
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
def generate_conferenceGUID():
	return random_string(8) + "-" + random_string(4) + "-" + random_string(4) + "-" + random_string(4) + "-" +  random_string(12)

# Generate random conferenceID
def generate_conferenceID():
	return randrange(1000,9999)
# Generate random numeric ID
def generate_numericID():
	return randrange(1000,9999)

def validate_newRecord(conferenceID,conferenceGUID,numericID):
	for element in systemConfigurationDb:
		for item in element:
			if conferenceGUID == item:
				return -1
			if conferenceID == item:
				return -2
			if numericID == item:
				return -3
	return 0


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
	if (params == 34):
		return fault_code(systemErrors[34],34)
	elif(params == 101):
		return fault_code(systemErrors[101],101)
	else:
	  	conferenceGUID = create_recordby_conferenceName(params)
	  	if (conferenceGUID!=-1):
	  		print "conference_create() API conference.create conferenceGUID:" + conferenceGUID
	  		logInfo(conferenceGUID)
	  		xmlResponse = {'conferenceGUID' :conferenceGUID}
			return xmlResponse
	  	else:
	  		return fault_code(systemErrors[4],4)

def conference_delete(msg):
	return msg

def conference_enumerate(msg):
	# 	Optional params could be: 	
	#					enumerateID  integer
	#					activeFilter boolean
	#	conferenceName,conferenceID,conferenceGUID,active,persistent,locked,numericID,registerWithGatekeeper,registerWithSIPRegistrar,h239ContributionEnabled,pin
	logInfo("conference_enumerate() API conference.enumerate")
	xmlResponse = {'conferenceName' :'AT&T TelePresence Solution connection test','conferenceID':45966,'conferenceGUID':'6b30aed0-be06-11e2-af9d-000d7c112b10','active':True,'persistent':False,'locked':False,
	'numericID':'8100','registerWithGatekeeper':False,'registerWithSIPRegistrar':False,'h239ContributionEnabled':False,'pin':''}
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
	  	xmlResponse = find_recordby_conferenceGUID(params)
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
