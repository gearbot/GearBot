import discord
import asyncio
import json
from . import protectedmessage
from . import configuration

def addcommand(server, command, text):
    try:
        if (command=='permissions'):
            return False
        check = False
        jsondata = None
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if i==server.id:
                    for x in jsondata[i]:
                        if x == command:
                            check = True
                    if not check:
                        jsondata[i].update(
                                                {
                                                    command:text
                                                }
                                           )
        if not check:
            configuration.writeconfig(jsondata)
            return True
    except Exception as e:
        print(e)
        raise e
    return False

def removecommand(server, command):
    try:
        if (command=='permissions'):
            return False
        check = False
        jsondata = None
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if i==server.id:
                    if command in jsondata[i]:
                        check = True
                        jsondata[i] = removekey(jsondata[i], command)
        if check:
            configuration.writeconfig(jsondata)
            return True
    except Exception as e:
        print(e)
        raise e
    return False

def getcommands(server):
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if i==server.id:
                    customcmd = jsondata[i]
                    customcmd = removekey(customcmd, 'Enable Logging')
                    customcmd = removekey(customcmd, 'Logging Channel ID')
                    customcmd = removekey(customcmd, 'Permissions')
                    return customcmd
    except Exception as e:
        print(e)
        raise e

def removekey(d, key):
    r = dict(d)
    del r[key]
    return r
