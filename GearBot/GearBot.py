import discord
import asyncio
import os
from functions import spam, protectedmessage, configuration

client = discord.Client()

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

@client.event
async def on_message(message):

    #Bot Information
    info = await client.application_info()
    checkBot = (info.name == 'SlakBotTest')

    #Config Command
    if message.content.startswith('!createconfig'):
        await configuration.resetconfig(message, client)

    if message.content.startswith('!readconfig'):
        await configuration.readconfig(message, client)

    if message.content.startswith('!resetconfig'):
        await configuration.resetconfig(message, client)
    
    #Check Spam
    if (not message.content.startswith('!')) & (not message.channel.is_private):
        await spam.check_for_spam(client, message, checkBot)

    #Basic Commands
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
