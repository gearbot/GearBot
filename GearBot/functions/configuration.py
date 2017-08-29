import discord
import asyncio
import json
import simplejson
from . import protectedmessage

async def createconfig(message, client):
    jsonfile = None
    try:
        jsonfile = open('config.json', 'a')

        if not (jsonfile is None):
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
            jsonfile.close()
    except FileNotFoundError:
        jsonfile = open('config.json', 'r')

        if not (jsonfile is None):
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
            jsonfile.close()
    except Exception as e:
        print(e)
        raise e

async def writeconfig(message, client, jsondata):
    with open('config.json', 'w') as jsonfile:
        jsonfile.write((simplejson.dumps(jsondata, indent=4, skipkeys=True, sort_keys=True)))
        jsonfile.close()

async def resetconfig(message, client):
    jsonfile = None
    check = False
    try:
        jsonfile = open('config.json', 'r')
        
        if not (jsonfile is None):
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if (i==message.channel.server.id):
                    check = True
                    jsondata[i]['Enable Logging'] = False
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

async def readconfig(message, client):
    jsonfile = None
    try:
        jsonfile = open('config.json', 'r')
        
        if not (jsonfile is None):
            jsondata = json.load(jsonfile)
            print(jsondata)
            for i in jsondata:
                print (i)
                for e in jsondata[i]:
                    print (e)
            jsonfile.close()
    except FileNotFoundError:
        print("Config file not found")
        pass
    except Exception as e:
        print(e)
        raise e
        
