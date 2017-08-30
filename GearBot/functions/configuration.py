import discord
import asyncio
import json
import simplejson
from . import protectedmessage

def hasconfig(server):
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if (i == server.id):
                    print('{} registered in config'.format(server.id))
                    return True
    except FileNotFoundError:
        print('Exception in hasConfig(): Server not registered in config')
        return False
    except Exception as e:
        print(e)
        raise e
    print('Server not registered in config...adding')
    return False

async def createconfig(message, client):
    jsonfile = None
    try:
        with open('config.json', 'a') as jsonfile:
            x = message.channel.server.id
            formattedjson = simplejson.dumps(
                                                {
                                                    x:{
                                                        "Enable Logging":True,
                                                        "Logging Channel ID":'0'
                                                    }
                                                }, indent=4, skipkeys=True, sort_keys=True)
            print (formattedjson)
            jsonfile.write(formattedjson)
            await protectedmessage.send_protected_message(client, message.channel, 'Succeeded')
    except FileNotFoundError:
        with open('config.json', 'w') as jsonfile:
            x = message.channel.server.id
            formattedjson = simplejson.dumps(
                                                {
                                                    x:{
                                                        "Enable Logging":True,
                                                        "Logging Channel ID":'0'
                                                    }
                                                }, indent=4, skipkeys=True, sort_keys=True)
            print (formattedjson)
            jsonfile.write(formattedjson)
            await protectedmessage.send_protected_message(client, message.channel, 'Succeeded')
    except Exception as e:
        print(e)
        raise e

async def createconfigserver(server):
    try:
        with open('config.json', 'a') as jsonfile:
            x = server.id
            formattedjson = simplejson.dumps(
                                                {
                                                    x:{
                                                        "Enable Logging":True,
                                                        "Logging Channel ID":'0'
                                                    }
                                                }, indent=4, skipkeys=True, sort_keys=True)
            print (formattedjson)
            jsonfile.write(formattedjson)
    except FileNotFoundError:
        with open('config.json', 'w') as jsonfile:
            x = server.id
            formattedjson = simplejson.dumps(
                                                {
                                                    x:{
                                                        "Enable Logging":True,
                                                        "Logging Channel ID":'0'
                                                    }
                                                }, indent=4, skipkeys=True, sort_keys=True)
            print (formattedjson)
            jsonfile.write(formattedjson)
    except Exception as e:
        print(e)
        raise e

async def writeconfig(message, client, jsondata):
    with open('config.json', 'w') as jsonfile:
        jsonfile.write((simplejson.dumps(jsondata, indent=4, skipkeys=True, sort_keys=True)))
        jsonfile.close()

async def isloggingenabled(message, client):
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if (i==message.channel.server.id):
                    return jsondata[i]['Enable Logging']
    except FileNotFoundError:
        print('Config file not found...creating')
        await createconfig(message, client)
        pass
    except Exception as e:
        print(e)
        
    return True

async def resetconfig(message, client):
    check = False
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if (i==message.channel.server.id):
                    check = True
                    jsondata[i]['Enable Logging'] = True
                    jsondata[i]['Logging Channel ID'] = '0'
            jsonfile.close()

            if check:
                await writeconfig(message, client, jsondata)
            else:
                await createconfig(message, client)
    except FileNotFoundError:
        print("Config file not found, creating a new 1")
        await createconfig(message, client)
        pass
    except Exception as e:
        print(e)
        raise e

async def getconfigvalues(message, client):
    try:
        with open('config.json') as jsonfile:
            jsondata = json.load(jsonfile)

            for i in jsondata:
                if (i==message.channel.server.id):
                    configvalues = simplejson.dumps(jsondata[i], indent=4, skipkeys=True, sort_keys=True)
                    await protectedmessage.send_protected_message(client, message.channel, '```' + configvalues + '```')
    except FileNotFoundError:
        print('Config file not found...creating')
        try:
            await createconfig(message, client)
            await getconfigvalues(message, client)
        except Exception as e:
            print(e)
            raise e
        pass
    except Exception as e:
        print(e)
        raise e

async def setloggingchannelid(message, client, channelid):
    check = False
    jsondata = None
    foundchannel = False
    for server in client.servers:
        for channel in server.channels:
            if channel.id == channelid:
                foundchannel = True
                try:
                    with open('config.json', 'r') as jsonfile:
                        jsondata = json.load(jsonfile)

                        for i in jsondata:
                            if (i==message.channel.server.id):
                                for x in jsondata[i]:
                                    if x == 'Logging Channel ID':
                                        jsondata[i][x] = channelid
                                        check = True
                    if check:
                        await writeconfig(message, client, jsondata)
                except FileNotFoundError:
                    print('Config file not found...creating')
                    try:
                        await createconfig(message, client)
                        await setloggingchannelid(message, client, channelid)
                    except Exception as e:
                        print(e)
                        raise e
                    pass
                except Exception as e:
                    print(e)
                    raise e
        if not foundchannel:
            await protectedmessage.send_protected_message(client, message.channel, 'Invalid channel ID')

#DEV ONLY COMMAND
async def readconfig(message, client):
    try:
        with open('config.json', 'r') as jsonfile:
        
            jsondata = json.load(jsonfile)
            print(jsondata)
            for i in jsondata:
                print (i)
                for e in jsondata[i]:
                    print (e)
    except FileNotFoundError:
        print("Config file not found")
        pass
    except Exception as e:
        print(e)
        raise e
            
        
