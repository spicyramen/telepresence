__author__ = 'gogasca'
from multiprocessing import Process, Lock, Queue
from multiprocessing.sharedctypes import Value, Array
from ctypes import Structure, c_double, c_int
import time
import random

class Line(Structure):
    _fields_ = [('x', c_double), ('y', c_double)]

class Point(Structure):
    _fields_ = [('x', c_double), ('y', c_double)]

counter = Queue(100)
def add():
    for x in range(1,5):
        counter.put(random.random())

def modify(n, x, s, A, L):
    n.value **= 2
    x.value **= 2
    s.value = s.value.upper()
    while True:
        time.sleep(3.0)
        print 'Wakeup - Size: ' + str(counter.__sizeof__())
        value = counter.get()
        if value is None:
            print 'None'
            counter.task_done()
            break
        else:
            print value
        for a in A:
            a.x **= 1
            a.y **= 1

        for l in L:
            l.x **= 1

if __name__ == '__main__':
    lock = Lock()

    n = Value('i', 7)
    x = Value(c_double, 1.0/3.0, lock=False)
    s = Array('c', 'hello world', lock=lock)
    A = Array(Point, [(1.875,-6.25), (-5.75,2.0), (2.375,9.5)], lock=lock)
    L = Array(Point, [(1,0)], lock=lock)
    #L.__setattr__([(1,1)])

    p = Process(target=modify, args=(n, x, s, A, L))
    o = Process(target=add)
    p.start()
    o.start()

    o.join()
    p.join()

    print n.value
    print x.value
    print s.value
    print [(a.x, a.y) for a in A]
    print [(l.x, l.y) for l in L]