__author__ = 'gogasca'

from xml.dom import minidom

doc = minidom.parse("../system.xml")

def getSysteMode():
    # doc.getElementsByTagName returns NodeList
    try:
        name = doc.getElementsByTagName("system")[0]
        print(name.firstChild.data)

        staffs = doc.getElementsByTagName("mode")[0]
        if staffs:
            print (staffs.firstChild.data)
        else:
            return -1
    except:
        pass
