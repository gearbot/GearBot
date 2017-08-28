import discord
import asyncio
import os
import message.protectedmessage as pmsg

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

async def check_for_spam(message, checkBot):
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
            
        await pmsg.send_protected_message(client, check, "The player {} is spamming a message similar to: ```{}```".format(message.author.mention, message.content))

@client.event
async def on_message(message):

    #Bot Information
    info = await client.application_info()
    checkBot = (info.name == 'SlakBotTest')

    #Check Spam
    if not message.content.startswith('!'):
        await check_for_spam(message, checkBot)

    #Basic Commands
    if message.content.startswith('!stop'):
        if((message.author.id == '140130139605434369')|(message.author.id == '106354106196570112')):
            await pmsg.send_protected_message(client, message.channel, 'Shutting down')
            await client.close()
    elif message.content.startswith("!upgrade"):
        if message.author.id == '106354106196570112':
            await pmsg.send_protected_message(client, message.channel, "I'll be right back with new gears!")
            file = open("upgradeRequest", "w")
            file.write("upgrade requested")
            file.close()
            await client.logout()
            await client.close()
        else:
            await pmsg.send_protected_message(client, message.channel, "While I like being upgraded i'm gona have to go with **ACCESS DENIED**")

#token = input("Please enter your Discord token: ")
token = os.environ['gearbotlogin']
client.run(token)
