import json

from functions import configuration


def haspermission(server, permission):
    jsondata = configuration.getconfig(server)
    if (permission.lower()) in jsondata[server.id]['Permissions']:
        return True
    return False

def removepermission(server, permission):
    jsondata = configuration.getconfig(server)
    if (permission.lower()) in jsondata[server.id]['Permissions']:
        jsondata = [x for x in jsondata[server.id]['Permissions'] if not (x==permission.lower())]
        configuration.writeconfig(jsondata)
        return True
    return False

def getpermissions(server):
    jsondata = configuration.getconfig(server)
    return jsondata[server.id]['Permissions']

def addpermission(server, permission):
    jsondata = configuration.getconfig(server)
    if not (permission.lower() in jsondata[server.id]['Permissions']):
        jsondata[server.id]['Permissions'].append(permission.lower())
        configuration.writeconfig(jsondata)
        return True
    return False
