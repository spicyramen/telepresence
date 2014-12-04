import xmlrpclib
import requests

'''
@author Gonzalo Gasca Meza
		AT&T Labs 
		Date: June 2013
		Emulates TelePresence Server 8710 API Calls
'''

hostname = '127.0.0.1'
port     = '8082'
url      = 'http://' + hostname + ':' + port + '/RPC2'
username = "sutapi"
password = "pwd22ATS!"

xmlRpcClient = xmlrpclib.ServerProxy(url,verbose=True,encoding='UTF-8')

def ping(msg):
  print xmlRpcClient.ping(msg)

def show_version():
  print xmlRpcClient.show_version()

def flex_participant_setMute():
    parameters = {'authenticationUser':username,'authenticationPassword':password,'participantID': 'cey7g1gf-to4g-376a-8pql-7y50nf0mwaj0'}
    params = tuple([parameters])
    xmlrpccall = xmlrpclib.dumps(params,'flex.participant.setMute',encoding='UTF-8')
    response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100,
                             stream = False, )
    if response.status_code == 200:
        result = xmlrpclib.loads( response.content, )[ 0 ]
        print result
    else:
  	    print '(flex.participant.setMute) Error'
  	    return -1

def flex_participant_destroy():
    parameters = {'authenticationUser':username,'authenticationPassword':password,'participantID': 'cey7g1gf-to4g-376a-8pql-7y50nf0mwaj0'}
    params = tuple([parameters])
    xmlrpccall = xmlrpclib.dumps(params,'flex.participant.destroy',encoding='UTF-8')
    response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100,
                             stream = False, )
    if response.status_code == 200:
        result = xmlrpclib.loads( response.content, )[ 0 ]
        print result
    else:
  	    print '(flex.participant.destroy) Error'
  	    return -1

def flex_participant_enumerate():
    # options
    # max
    # cookie
    # conferenceId

    parameters = {'authenticationUser':username,'authenticationPassword':password}
    params = tuple([parameters])
    xmlrpccall = xmlrpclib.dumps(params,'flex.participant.enumerate',encoding='UTF-8')
    response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100,
                             stream = False, )
    if response.status_code == 200:
        result = xmlrpclib.loads( response.content, )[ 0 ]
        print result
    else:
  	    print '(flex.participant.enumerate) Error'
  	    return -1

#= 'http://12.120.192.135:9311/RPC2'
def feedbackReceiver_configure(uri):
  if uri:
    receiverUri = uri
  else:
    receiverUri = 'http://12.120.192.135:9311/RPC2'

  sourceIdentifier = 'TEMPSRCID'
  parameters = {'receiverIndex': -1,'sourceIdentifier':sourceIdentifier,'receiverURI':receiverUri,'authenticationUser':username,'authenticationPassword':password}
  params = tuple([parameters])
  xmlrpccall = xmlrpclib.dumps(params,'feedbackReceiver.configure',encoding='UTF-8')
  response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100,
                             stream = False, )
  if response.status_code == 200:
    result = xmlrpclib.loads( response.content, )[ 0 ]
    print result
  else:
  	print '(feedbackReceiver.configure) Error'
  	return -1

def conference_create(conferenceName):
    # Verify conferenceName syntax
  '''if len(conferenceGUID)>80 and not isinstance(conferenceName, str):
    print "Invalid conferenceGUID value"
    return -1
  '''
  if len(conferenceName)>80 and not isinstance(conferenceName, str):
      return

  parameters = {'conferenceName' :conferenceName,'authenticationUser':username,'authenticationPassword':password}
  params = tuple([parameters])
  xmlrpccall = xmlrpclib.dumps(params,'conference.create',encoding='UTF-8')
  response = requests.request( 'POST', url,
                             data = xmlrpccall,
                             headers = { 'Content-Type': 'application/xml' },
                             timeout = 100, 
                             stream = False, )
  if response.status_code == 200:
    result = xmlrpclib.loads( response.content, )[ 0 ]
    print result
  else:
    print '(conference.create) Error'
    return -1 

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
    #ping("REQUEST")
    for x in range(1,1000,1):
        show_version()
        #feedbackReceiver_configure('http://12.120.192.135:9311/RPC2')
        flex_participant_enumerate()
        #flex_participant_setMute()
        #flex_participant_destroy()
        #flex_participant_enumerate()
    #conference_create("AT&T TelePresence")
    #conference_enumerate()
    #conference_status("rqdor4jk-aho7-9rap-hodd-je5pbt2ulypp")

except Exception as err:
    print("A fault occurred!")
    print "%s" % err

