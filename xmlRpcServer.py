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


hostname = "localhost"
port     = 8080
version  = '3.0(58)'
configurationFile = 'configuration.xml'
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

# Run the server's main loop
def start_xmplrpc():
	print "Cisco TelePresence Server 8710 Emulator started...."
	print "Hostname: " + hostname +  " Port: " + str(port)
	print "Version:  " + version
	try:		
		print "XML-RPC Server initialized..."
		threading.Thread(target=server.serve_forever()).start()
	except KeyboardInterrupt:
		print "Cisco TelePresence Server 8710 Emulator stopping...."
	except Exception, e:
		print "Exception: " + str(e)

# Verify configuration file
def read_configuration():
	print "Reading system configuration..."
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
			print 'validate_config() Valid param: ' + param
		else:
			print 'validate_config() Invalid param: ' + param
			return -1

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

# Verify records in file
def validate_data(filerecords):

	print "Validating system configuration data..."
	file_len(configurationFile)
	print "validate_data() Processing " + str(file_len(configurationFile) -1 ) + " record(s)..."
	del filerecords[0]
	if len(filerecords)<1:
		return -1
	for record in filerecords:
		print record
		paramNumber = 0
		if len(record) == 21:
			for field in record:
				if paramNumber == 12 and field == "''": # No PIN					
					paramNumber += 1			
				elif castRecordElement(field) == dataType[paramNumber]:					
					paramNumber += 1    						
    			else:
    				if paramNumber!=21:
	    				print "validate_data() Invalid data paramNumber: " + str(paramNumber)
    					return -1
		else:
			print "Invalid record " + record
			return -1	

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

def conference_enumerate(params):
	response = {'conferenceName' :'AT&T TelePresence Solution connection test','conferenceID':45966,'conferenceGUID':'6b30aed0-be06-11e2-af9d-000d7c112b10','active':True,'persistent':False,'locked':False,
	'numericID':'8100','registerWithGatekeeper':False,'registerWithSIPRegistrar':False,'h239ContributionEnabled':False,'pin':''}
	return response

def conference_status(conferenceGUID):
	if len(conferenceGUID)!=36 and not isinstance(conferenceGUID, str):
  		print "Invalid conferenceGUID value"
  	
	response = {'portsContentFree': 24, 'locked': False, 'oneTableMode': 0, 'portsAudioFree': 10, 'roundTableEnable': False, 'videoPortLimit': 0, 'conferenceID': 1000, 'persistent': True, 'portsVideoFree': 24, 'audioPortLimit': 0, 'conferenceGUID': '8ca0c690-dd82-11e2-84f9-000d7c112b10', 'audioPortLimitSet': False, 'pin': '', 'active': True, 'videoPortLimitSet': False, 'registerWithGatekeeper': True, 'numericID': '8100', 'participantList': [], 'recording': False, 'registerWithSipRegistrar': True, 'h239ContributionID': 0}
	return response

# Register an instance; all the methods of the instance are published as XML-RPC methods (in this case, just 'div').
class Methods:
    def show_version(self):
        return version

# Create server
server = SimpleXMLRPCServer((hostname, port),requestHandler=RequestHandler,logRequests=True)
server.register_function(ping_function, 'ping')
server.register_function(conference_enumerate, 'conference.enumerate')
server.register_function(conference_status, 'conference.status')
server.register_introspection_functions()
server.register_instance(Methods())

# Start
try:
	_init_()
	start_xmplrpc()
except KeyboardInterrupt:
	print "Cisco TelePresence Server 8710 Emulator stopping...."
except Exception,e:
	print "Exception found " + str(e)
