from . import *

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

    #REMOVES MESSAGES WHEN SPAM IS DETECTED
    if (count > 3):
        for msg in repeatedMessages:
            try:
                await client.delete_message(msg)
            except Exception as e:
                print("Exception: {} while trying to delete the messages".format(str(e)))

    #LOG SPAMMED MESSAGE IN LOGGING CHANNEL
    if (count > 3):
        if(configuration.isloggingenabled(message.channel.server)):
            check = client.get_channel(configuration.getloggingchannelid(message.channel.server))
            if (check=='0'):
                check = None
                
            if not (check is None):
                await protectedmessage.send_protected_message(client, check, "The player {} is spamming a message similar to: ```{}```".format(message.author.mention, message.content))
