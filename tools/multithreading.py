__author__ = 'gogasca'
from multiprocessing import Process
import random
import time

def some_function(first, last):
    time.sleep(random.randint(1, 10))
    print first, last

processes = []

for m in range(1,16):
       n = m + 1
       p = Process(target=some_function, args=(m, n))
       p.start()
       processes.append(p)

for p in processes:
       p.join()