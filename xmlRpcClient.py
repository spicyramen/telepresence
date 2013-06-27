import xmlrpclib
import requests

'''
@author Gonzalo Gasca Meza
		AT&T Labs 
		Date: June 2013
		Emulates TelePresence Server 8710 API Calls
'''

hostname = 'localhost'
port     = '8080'
url      = 'http://' + hostname + ':' + port + '/RPC2'
username = "sut"
password = "1qaz2wsx"

xmlRpcClient = xmlrpclib.ServerProxy(url,verbose=True,encoding='UTF-8')

def ping(msg):
  print xmlRpcClient.ping(msg)

def show_version():
  print xmlRpcClient.show_version()

def conference_create():
  print xmlRpcClient.conference.create()  

def conference_enumerate():
  parameters = {'activeFilter' :False,'authenticationUser':username,'authenticationPassword':password}
  params = tuple([parameters])
  xmlrpccall = xmlrpclib.dumps(params,'conference.enumerate',encoding='UTF-8')
  response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100, 
                             stream = False, )
  if response.status_code == 200:
    result = xmlrpclib.loads( response.content, )[ 0 ]
    print result
  else:
  	print '(conference.enumerate) Error'
  	return -1


def conference_status(conferenceGUID):
  # Verify conferenceGUID syntax
  '''if len(conferenceGUID)!=36 and not isinstance(conferenceGUID, str):
  	print "Invalid conferenceGUID value"
  	return -1
  '''
  if len(conferenceGUID)!=36 and not isinstance(conferenceGUID, str):
      return

  parameters = {'conferenceGUID' :conferenceGUID,'authenticationUser':username,'authenticationPassword':password}
  params = tuple([parameters])
  xmlrpccall = xmlrpclib.dumps(params,'conference.status',encoding='UTF-8')
  response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100, 
                             stream = False, )
  if response.status_code == 200:
    result = xmlrpclib.loads( response.content, )[ 0 ]
    print result
  else:
  	print '(conference.status) Error'
  	return -1

# Print list of available methods
def list_methods():
  print xmlRpcClient.system.listMethods()

try:
    show_version()
    conference_create()
    conference_enumerate()
    conference_status("8ca0c690-dd82-11e2-84f9-000d7c112b19")
except Exception as err:
    print("A fault occurred!")
    print "%s" % err

