import discord
import asyncio
from . import protectedmessage
from . import configuration

async def check_for_spam(client, message, checkBot):
    text = message.content
    text = text.replace(" ","")
    text = text.lower()
    repeatedMessages = []
    count = 0

    async for log in client.logs_from(message.channel, limit=30):
        if not (log.author.bot):
            text2 = log.content
            text2 = text2.replace(" ","")
            text2 = text2.lower()
            if ((text == text2) & (message.author.id == log.author.id)):
                repeatedMessages.append(log)
                count+=1

    #REMOVES MESSAGES WHEN SPAM IS DETECTED DEVELOPER ONLY!
    if checkBot:
        if (count > 3):
            for msg in repeatedMessages:
                try:
                    await client.delete_message(msg)
                except Exception as e:
                    print("Exception: {} while trying to delete the messages".format(str(e)))

    #LOG SPAMMED MESSAGE IN LOGGING CHANNEL
    
    if (count > 3):
        if((await configuration.isloggingenabled(message, client))):
            check = None
        
            #DEV
            if checkBot:
                for channel in message.server.channels:
                    if (channel.server == message.server) & (channel.name == 'logging'):
                        check = channel
                if check is None:
                   await client.create_channel(message.server, 'logging')
                   for channel in message.server.channels:
                       if channel.name == 'logging':
                           check = channel
            #BC
            else:
                try:
                    check = client.get_channel('349517224320565258')
                except Exception as e:
                    print("Exception: {} while trying to get a certain channel id: ISSUE FIXED AUTOMATICALLY".format(str(e)))
                    checkBot = True
                    pass
            await protectedmessage.send_protected_message(client, check, "The player {} is spamming a message similar to: ```{}```".format(message.author.mention, message.content))
