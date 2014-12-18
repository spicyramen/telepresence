__author__ = 'gogasca'
import __builtin__
"""
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
print id"""

apple = [["a","b","c"],[1,2,3,4,5,6],["antony","max","sandra","sebastian"],[{'gonzalo':'bad boy'}]]

dict = {'gonzalo':'good boy'}
loco = apple[3][0]['gonzalo']
print loco

#print type(dict)
if 'gonzalo' in dict.keys():
    print 'fuck'

for element in apple:
    #print type(element)
    if type(element[0]) is __builtin__.dict:
        print 'Found a dictionary!'
    else:
        print type(element[0])
        print 'Not a dict'