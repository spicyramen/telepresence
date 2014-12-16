__author__ = 'gogasca'

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
import time, string, csv, threading, logging, copy, re,os
import xmlrpclib
import requests

hostname = "127.0.0.1"
port = 9311
version = '1.0(0)'

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

# Run the server's main loop
def startXmlRpc():
    logging.info("FeedBackServer started....")
    print "FeedBackServer started...."
    logging.info("Hostname: " + hostname + " Port: " + str(port))
    print "Hostname: " + hostname + " Port: " + str(port)
    logging.info("API Version:  " + version)
    print "API Version:  " + version
    try:
        logging.info("XML-RPC Server initialized...")
        threading.Thread(target=server.serve_forever()).start()
    except KeyboardInterrupt:
        logging.info("FeedBackServer stopping xml service....")
    except Exception as instance:
        print type(instance)
        print instance.args
        logging.error("startXmlRpc() Exception: " + str(instance))
        raise SystemExit

# Logging info
def logInfo(msg):
    logging.info(msg)

def fault_code(string, code):
    xmlResponse = {'faultCode': code, 'faultString': string}
    logInfo(xmlResponse)
    return xmlResponse

def eventNotification(msg):
    print "eventNotification() API eventNotification"
    logInfo("eventNotification() API eventNotification")
    # Optional parameters:
    params = copy.deepcopy(msg)
    # Mandatory
    xmlResponse = []

    if (params == 34):
        return fault_code(systemErrors[34], 34)
    elif (params == 101):
        return fault_code(systemErrors[101], 101)
    else:
        #Participants
        # Verify authentication and then collect other parameters
        for element in params:
            if element == 'sourceIdentifier':
                logging.info('sourceIdentifier param found')
                sourceIdentifier = True
            if element == 'events':
                logging.info('events param found')

        print params
        if (sourceIdentifier):
            xmlResponse = {'status': True}
            return xmlResponse
        else:
            logging.error('eventNotification  not found')
            return fault_code(systemErrors[5], 5)

server = SimpleXMLRPCServer((hostname, port), requestHandler=XmlRequestHandler, logRequests=True)
server.register_function(eventNotification, 'eventNotification')


def feedbackServer():
    logging.basicConfig(filename='logs/feedback.log', level=logging.INFO,
                        format='%(asctime)s.%(msecs).03d %(levelname)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    logging.info("-----------------------Initializing FeedBackServer server------------------------")
    print "-----------------------Initializing FeedBackServer server------------------------"
    try:
        """start"""

        xml = Process(target=startXmlRpc)
        """Start eventNotification"""
        xml.start()
        xml.join()
    except KeyboardInterrupt:
        print "FeedBackServer stopping...."
        logging.info("FeedBackServer stopping....")
    except Exception, e:
        print "Exception found" + str(e)
        logging.exception("Exception found " + str(e))

if __name__ == '__main__':
    feedbackServer()