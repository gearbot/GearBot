import json

from . import configuration


def addcommand(server, command, text):
    if not (command=='permissions'):
        jsondata = configuration.getconfig(server)
        if not (command in jsondata[server.id]):
            jsondata[server.id].update(
                                            {
                                                command:text
                                            }
                                      )
            configuration.writeconfig(jsondata)
            return True
    return False

def removecommand(server, command):
    if not (command=='permissions'):
        jsondata = configuration.getconfig(server)
        if command in jsondata[server.id]:
            jsondata[server.id] = removekey(jsondata[server.id], command)
            configuration.writeconfig(jsondata)
            return True
    return False

def getcommands(server):
    jsondata = configuration.getconfig(server)
    customcmd = jsondata[server.id]
    customcmd = removekey(customcmd, 'Enable Logging')
    customcmd = removekey(customcmd, 'Logging Channel ID')
    customcmd = removekey(customcmd, 'Permissions')
    return customcmd

def removekey(d, key):
    r = dict(d)
    del r[key]
    return r
