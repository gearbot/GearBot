import discord
import asyncio
import os
from functions import spam, protectedmessage, configuration

client = discord.Client()
checkBot = None
info = None

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

    for server in client.servers:
        if not configuration.hasconfig(server):
            await configuration.createconfigserver(server)

    global info
    info = await client.application_info()
    global checkBot
    checkBot = (info.name == 'SlakBotTest')
        

@client.event
async def on_message(message):

    #Check Spam
    if (not message.content.startswith('!')) & (not message.channel.is_private):
        await spam.check_for_spam(client, message, checkBot)
        
    #Config Command
    if message.content.startswith('!getconfig'):
        await configuration.getconfigvalues(message, client)

    if message.content.startswith('!resetconfig'):
        await configuration.resetconfig(message, client)

    if (message.content.startswith('!setloggingchannelid')) & (len( (message.content.split()) ) == 2):
        await configuration.setloggingchannelid(message, client, (message.content.split()[1]))

    #Basic Commands
    if message.content.startswith('!help'):
        text = """```!help: Display all the commands\n!upgrade: Update the bot to the latest version\n!stop: Disconnect the bot\n!resetconfig: Reset the server's custom config to the basic config\n!setloggingchannelid (id): Change the logging channel to a channel of your choice```"""
        await protectedmessage.send_protected_message(client, message.channel, text)
    if message.content.startswith('!stop'):
        if((message.author.id == '140130139605434369')|(message.author.id == '106354106196570112')):
            await protectedmessage.send_protected_message(client, message.channel, 'Shutting down')
            await client.close()
    elif message.content.startswith("!upgrade"):
        if message.author.id == '106354106196570112':
            await protectedmessage.send_protected_message(client, message.channel, "I'll be right back with new gears!")
            file = open("upgradeRequest", "w")
            file.write("upgrade requested")
            file.close()
            await client.logout()
            await client.close()
        else:
            await protectedmessage.send_protected_message(client, message.channel, "While I like being upgraded i'm gona have to go with **ACCESS DENIED**")

try:
    token = os.environ['gearbotlogin']
except KeyError:
    token = input("Please enter your Discord token: ")
client.run(token)
