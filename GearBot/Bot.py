import discord
import asyncio
import os

from functions import configuration, protectedmessage, permissions, spam, customcommands

client = discord.Client()
checkBot = None
info = None


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    print('Do not create custom commands that might interfere with the commands of other bots')
    print('You can report an Issue/Bug on the GearBot repository of AEnterprise on GitHub')
    print('This bot is made by Slak#9006 & AEnterprise#4693')
    print('------')

    for server in client.servers:
        if not configuration.hasconfig(server):
            configuration.createconfigserver(server)

    global info
    info = await client.application_info()
    global checkBot
    checkBot = (info.name == 'SlakBotTest')


@client.event
async def on_message(message):
    permission = False
    if not message.author.bot:
        li = list(permissions.getpermissions(message.channel.server))
        for permissionrole in li:
            for role in message.author.roles:
                if permissionrole == role.name.lower():
                    permission = True

    if message.author == message.channel.server.owner:
        permission = True

    # Check Spam
    if (not message.content.startswith('!')) & (not message.channel.is_private):
        await spam.check_for_spam(client, message, checkBot)

    # Commands that require permissions
    if (permission | (message.author == message.channel.server.owner)) & (
        message.content.startswith('!') & (not message.channel.is_private)):
        receivedmessage = message.content.lower()

        # Custom commands ----------------------------------------------------------------------------------------------------------------------------------------------------------
        if receivedmessage.startswith('!add') & (len(message.content.split()) >= 3):
            if customcommands.addcommand(message.channel.server, message.content.split()[1].lower(),
                                         message.content.split(' ', 2)[2]):
                await protectedmessage.send_protected_message(client, message.channel,
                                                              "Added the command: `{}` succesfully".format(
                                                                  message.content.split()[1].lower()))
            else:
                await protectedmessage.send_protected_message(client, message.channel,
                                                              "Command wasn't added because the command is already registered or invalid")

        elif receivedmessage.startswith('!remove') & (len(message.content.split()) == 2):
            if customcommands.removecommand(message.channel.server, message.content.split()[1].lower()):
                await protectedmessage.send_protected_message(client, message.channel,
                                                              "Removed the command: `{}` succesfully".format(
                                                                  message.content.split()[1].lower()))
            else:
                await protectedmessage.send_protected_message(client, message.channel,
                                                              "This custom command does not exist or is equal to a similar config value")

                # Permission commands -----------------------------------------------------------------------------------------------------------------------------------------------------
        elif (receivedmessage.startswith('!addpermission')) & (len(message.content.split()) >= 2):
            if message.author == message.channel.server.owner:
                permissions.addpermission(message.channel.server, (message.content.split(' ', 1)[1]))
            else:
                await protectedmessage.send_protected_message(client, message.channel,
                                                              'Only the owner is allowed to add a permission role')

        elif (receivedmessage.startswith('!removepermission')) & (len(message.content.split()) >= 2):
            if message.author == message.channel.server.owner:
                permissions.removepermission(message.channel.server, (message.content.split(' ', 1)[1]))
            else:
                await protectedmessage.send_protected_message(client, message.channel,
                                                              'Only the owner is allowed to remove a permission role')

        # Config -------------------------------------------------------------------------------------------------------------------------------------------------------------------
        elif receivedmessage.startswith('!getconfig'):
            await protectedmessage.send_protected_message(client, message.channel,
                                                          (configuration.getconfigvalues(message.channel.server)))

        elif receivedmessage.startswith('!resetconfig'):
            configuration.resetconfig(message.channel.server)

        # Logging ------------------------------------------------------------------------------------------------------------------------------------------------------------------
        elif (receivedmessage.startswith('!setloggingchannelid')) & (len((message.content.split())) == 2):
            if configuration.setloggingchannelid(message.channel.server, client, (message.content.split()[1])):
                await protectedmessage.send_protected_message(client, message.channel, 'Logging channel changed')

        elif receivedmessage.startswith('!togglelogging'):
            if configuration.togglelogging(message.channel.server):
                await protectedmessage.send_protected_message(client, message.channel, 'Logging enabled')
            else:
                await protectedmessage.send_protected_message(client, message.channel, 'Logging disabled')

        # Updating & Stop ----------------------------------------------------------------------------------------------------------------------------------------------------------
        elif receivedmessage.startswith('!stop'):
            if (message.author.id == '140130139605434369') | (message.author.id == '106354106196570112') | (
                message.author == message.channel.server.owner):
                await protectedmessage.send_protected_message(client, message.channel, 'Shutting down')
                await client.close()

        elif receivedmessage.startswith("!upgrade"):
            if message.author.id == '106354106196570112':
                await protectedmessage.send_protected_message(client, message.channel,
                                                              "I'll be right back with new gears!")
                file = open("upgradeRequest", "w")
                file.write("upgrade requested")
                file.close()
                await client.logout()
                await client.close()
            else:
                await protectedmessage.send_protected_message(client, message.channel,
                                                              "While I like being upgraded i'm gona have to go with **ACCESS DENIED**")

        # Custom commands ----------------------------------------------------------------------------------------------------------------------------------------------------------
        else:
            customcmd = customcommands.getcommands(message.channel.server)
            formattedmsg = message.content.lower()
            formattedmsg = (formattedmsg[1::])
            if formattedmsg in customcmd:
                await protectedmessage.send_protected_message(client, message.channel, customcmd[formattedmsg])

    # Basic Command
    if message.content.lower().startswith('!help'):
        text = None
        if permission:
            text = '```!help: Display all the commands\n' \
                   '!upgrade: Update the bot to the latest version\n' \
                   '!stop: Disconnect the bot\n' \
                   '!add (command) (text): Add a new custom command\n' \
                   '!remove (command): Remove a custom command\n' \
                   '!getconfig: Look at the current configuration\n' \
                   '!resetconfig: Reset the configuration to it\'s defaults\n' \
                   '!setloggingchannelid (id): Change the logging channel to a channel of your choice\n' \
                   '!togglelogging: Enable/Disable logging\n' \
                   '!getcustomcommands: Retreive all the custom commands\n' \
                   '!(custom command): Execute a custom command```'
        else:
            text = '```!help: Display all the commands\n' \
                   '!getcustomcommands: Retreive all the custom commands\n' \
                   '!(custom command): Execute a custom command```'
        if not (text is None):
            await protectedmessage.send_protected_message(client, message.channel, text)


try:
    token = os.environ['gearbotlogin']
except KeyError:
    token = input("Please enter your Discord token: ")
client.run(token)
