__author__ = 'gogasca'
id = []
def generateId():
        global id
        id = range(1,11,1)
        print id


generateId()
try:
    del id[0]
except:
    pass
print id

try:
    del id[0]
except:
    pass
print id