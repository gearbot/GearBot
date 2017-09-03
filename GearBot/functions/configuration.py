import json

import simplejson

def getconfig(server):
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            if not (server.id in jsondata):
                createconfigserver(server, False)
                return getconfig(server)
            return jsondata
    except FileNotFoundError:
        createconfigserver(server, True)
        return getconfig(server)
    except Exception as e:
        print(e)
        raise e

def hasconfig(server):
    jsondata = getconfig(server)
    if server.id in list(jsondata):
        print('{} registered in config'.format(server.id))
        return True
    return False

def getloggingchannelid(server):
    jsondata = getconfig(server)
    return jsondata[server.id]['Logging Channel ID']

def writeconfig(jsondata):
    with open('config.json', 'w') as jsonfile:
        jsonfile.write((simplejson.dumps(jsondata, indent=4, skipkeys=True, sort_keys=True)))
        jsonfile.close()

def createconfigserver(server, create):
    if create:
        writeconfig(
                        {
                            server.id:{
                                "Enable Logging":True,
                                "Logging Channel ID":'0',
                                "Permissions":([])
                            }
                        }
                    )
    else:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            jsonfile.close()
        jsondata.update(    {
                                server.id:{
                                    "Enable Logging":True,
                                    "Logging Channel ID":'0',
                                    "Permissions":([])
                                }
                            }
                        )
        writeconfig(jsondata)

def isloggingenabled(server):
    jsondata = getconfig(server)
    if server.id in jsondata:
        return jsondata[server.id]['Enable Logging']
    return False

def resetconfig(server):
    jsondata = getconfig(server)
    if server.id in jsondata:
        jsondata[server.id]['Enable Logging'] = True
        jsondata[server.id]['Logging Channel ID'] = '0'
        jsondata[server.id]['Permissions'] = ([])
        writeconfig(jsondata)

def getconfigvalues(server):
    jsondata = getconfig(server)
    return simplejson.dumps(jsondata[server.id], indent=4, skipkeys=True, sort_keys=True)

def setloggingchannelid(server, client, channelid):
    if client.get_channel(channelid) in server.channels:
        jsondata = getconfig(server)
        jsondata[server.id]['Logging Channel ID'] = channelid
        writeconfig(jsondata)
        return True
    return False

def togglelogging(server):
    jsondata = getconfig(server)
    currentstate = jsondata[server.id]['Enable Logging']
    if currentstate:
        jsondata[server.id]['Enable Logging'] = False
    else:
        jsondata[server.id]['Enable Logging'] = True
    writeconfig(jsondata)
    return (not currentstate)
            
            
        
