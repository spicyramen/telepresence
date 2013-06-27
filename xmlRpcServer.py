'''
@author Gonzalo Gasca Meza
		AT&T Labs 
		Date: June 2013
		Emulates TelePresence Server 8710 Server API
'''

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from types import *
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


# Restrict to a particular path.

class RequestHandler(SimpleXMLRPCRequestHandler):
	rpc_paths = ('/RPC2',)

###########################################################################################
# System configuration
###########################################################################################

def _init_():
	if read_configuration() == -1:
		print "Error invalid configuration"
		logging.warning("Error invalid configuration")

# Run the server's main loop
def start_xmplrpc():
	logging.info("Cisco TelePresence Server 8710 Emulator started....")
	logging.info("Hostname: " + hostname +  " Port: " + str(port))
	logging.info("Version:  " + version)
	try:		
		logging.info("XML-RPC Server initialized...")
		threading.Thread(target=server.serve_forever()).start()
	except KeyboardInterrupt:
		print ""
		logging.info("Cisco TelePresence Server 8710 Emulator stopping....")
	except Exception, e:
		print ""
		logging.error("Exception: " + str(e))

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
			print ""
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


#Verifies authentication
def xml_handler(msg):
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
def find_param_conference(param):
	if param >= 0 and param < len(conferenceParameters):
		return conferenceParameters[param]
	else:
		return -1

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
	if msg == 'REQUEST':
	 return 'REPLY'
	else:
	 return 'INVALID MESSAGE: ' + msg

def conference_enumerate(msg):
	# 	Optional params could be: 	
	#					enumerateID  integer
	#					activeFilter boolean
	#	conferenceName,conferenceID,conferenceGUID,active,persistent,locked,numericID,registerWithGatekeeper,registerWithSIPRegistrar,h239ContributionEnabled,pin
	print("conference_enumerate() API conference.enumerate")
	logInfo("conference_enumerate() API conference.enumerate")
	response = {'conferenceName' :'AT&T TelePresence Solution connection test','conferenceID':45966,'conferenceGUID':'6b30aed0-be06-11e2-af9d-000d7c112b10','active':True,'persistent':False,'locked':False,
	'numericID':'8100','registerWithGatekeeper':False,'registerWithSIPRegistrar':False,'h239ContributionEnabled':False,'pin':''}
	return response

def conference_status(msg):
	# 	Verify conferenceGUID status
	print("conference_status() API conference.status ")
	logInfo("conference_status() API conference.status ")
	params = xml_handler(msg)
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
server = SimpleXMLRPCServer((hostname, port),requestHandler=RequestHandler,logRequests=True)
server.register_function(ping_function, 'ping')
server.register_function(conference_enumerate, 'conference.enumerate')
server.register_function(conference_status, 'conference.status')
server.register_introspection_functions()
server.register_instance(Methods())

def main():

	logging.basicConfig(filename='tpsServer.log', level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')	
	logging.info("-----------------------Initializing system------------------------")
	print("-----------------------Initializing system------------------------")
	try:
		_init_()
		start_xmplrpc()		
	except KeyboardInterrupt:
		print ""
		logging.info ("Cisco TelePresence Server 8710 Emulator stopping....")
	except Exception,e:
		print ""
		logging.error("Exception found " + str(e))

if __name__ == '__main__':
    main()