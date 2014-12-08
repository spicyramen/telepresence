from multiprocessing import Process, Queue

def f(q):
    q.put([42, None, 'hello'])
    q.put([11,None,'bye'])

if __name__ == '__main__':
    q = Queue()
    p = Process(target=f, args=(q,))
    p.start()
    print q.get()    # prints "[42, None, 'hello']"
    print q.get()    # prints "[42, None, 'hello']"
    p.join()