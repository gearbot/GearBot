import discord
import asyncio
import json
import simplejson
from . import protectedmessage

async def createconfig(message, client):
    jsonfile = None
    try:
        jsonfile = open('config.json', 'w')

        if not (jsonfile is None):
            x = message.channel.server.id
            formattedjson = simplejson.dumps(
                                                {
                                                    x:dict(
                                                        ErrorMessage='',
                                                        LogIdentifier='123'
                                                    )
                                                }, indent=4, skipkeys=True, sort_keys=True)
            print (formattedjson)
            jsonfile.write(formattedjson)
            await protectedmessage.send_protected_message(client, message.channel, 'Succeeded')
            jsonfile.close()
    except Exception as e:
        print(e)
        raise e
        
