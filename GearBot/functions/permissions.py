import discord
import asyncio
import json
from . import configuration

def haspermission(server, permission):
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if i==server.id:
                    for x in jsondata[i]:
                        if x == 'Permissions':
                            li = jsondata[i][x]
                            if (permission.lower()) in li:
                                return True
                            return False
    except (KeyError, TypeError):
        print('Invalid parameters are used while readng a permission')
    except Exception as e:
        print(e)
        raise e
    return False

def getpermissions(server):
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if i==server.id:
                    for x in jsondata[i]:
                        if x == 'Permissions':
                            return jsondata[i][x]
    except Exception as e:
        print(e)
        raise e
    return []

def addpermission(server, permission):
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            for i in jsondata:
                if i==server.id:
                    for x in jsondata[i]:
                        if x == 'Permissions':
                            li = jsondata[i][x]
                            if not (permission.lower() in li):
                                li.append(permission.lower())
                                jsondata[i][x] = li
                                configuration.writeconfig(jsondata)
    except Exception as e:
        print(e)
        raise e
    return False
