from distutils.version import LooseVersion
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

def getSortedVersions(versions):
    return sorted(list(versions.keys()), key=cmp_to_key(compareVersions))

def getSortedVersionsArray(versions):
    return sorted(list(versions), key=cmp_to_key(compareVersions))

def getLatest(versions):
    result = getSortedVersions(versions)
    return result[0] if len(result) > 0 else None

def getLatestArray(versions):
    result = getSortedVersionsArray(versions)
    return result[0] if len(result) > 0 else None