import json

from distutils.version import LooseVersion

versions:dict = dict()

def initVersionInfo():
    try:
        with open('versions.json', 'r') as jsonfile:
            global versions
            versions = json.load(jsonfile)
    except FileNotFoundError:
        saveVersionInfo()
        initVersionInfo()
    except Exception as e:
        print(e)
        raise e

def saveVersionInfo():
    global versions
    with open('versions.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(versions, indent=4, skipkeys=True, sort_keys=True)))

def compareVersions(v1, v2):
    return LooseVersion(v1) > LooseVersion(v2)

def cmp_to_key(mycmp):
    'Convert a cmp= function into a key= function'
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj
        def __lt__(self, other):
            return mycmp(self.obj, other.obj) > 0
        def __gt__(self, other):
            return mycmp(self.obj, other.obj) < 0
        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0
        def __le__(self, other):
            return mycmp(self.obj, other.obj) >= 0
        def __ge__(self, other):
            return mycmp(self.obj, other.obj) <= 0
        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K

def getSortedVersions():
    return sorted(list(versions.keys()), key=cmp_to_key(compareVersions))

def getLatest():
    return versions[getSortedVersions()[0]]