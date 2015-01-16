from multiprocessing import Process, Lock
from multiprocessing.sharedctypes import Value, Array
from ctypes import Structure, c_double,c_char_p

class Point(Structure):
    _fields_ = [('x', c_double), ('y', c_double)]

class Call(Structure):
    #([participantID, conferenceID, accessLevel,displayName,connectionState,calls,addresses])
    _fields_ = [('participantId',c_char_p),('conferenceID',c_char_p),('accessLevel',c_char_p),('displayName',c_char_p),('connectionState',c_char_p),('calls',c_char_p),('addresses',c_char_p)]

def modify(n,s):
    n.value **= 2
    #x.value **= 2
    s.value = s.value.upper()
    #for a in A:
    #    a.x **= 2
    #    a.y **= 2

if __name__ == '__main__':
    lock = Lock()
    n = Value('i', 7)
   #x = Value(c_double, 1.0/3.0, lock=False)
    s = Array('c', 'hello world', lock=lock)
    A = Array(Call,[('93c5zh0r-u5lu-och7-ihy7-ln4w8gqxdeix',)], lock=lock)
    #participantId = 'Ciao'
   #A = Array(Point, [(1.875,-6.25), (-5.75,2.0), (2.375,9.5)], lock=lock)

    p = Process(target=modify, args=(n,s))
    p.start()
    p.join()

    print n.value
  #  print x.value
    print s.value
    print [(a.participantId) for a in A]