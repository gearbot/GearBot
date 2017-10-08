from Util import GearbotLogging
import Variables


async def check_for_spam(client, message):
    text = message.content
    text = text.replace(" ","")
    text = text.lower()
    repeatedMessages = []
    count = 0

    async for log in client.logs_from(message.channel, limit=6):
        if not (log.author.bot):
            text2 = log.content
            text2 = text2.replace(" ","")
            text2 = text2.lower()
            if (text == text2) and (message.author.id == log.author.id):
                repeatedMessages.append(log)
                count+=1

    #REMOVES MESSAGES WHEN SPAM IS DETECTED
    if (count > 3):
        try:
            for msg in repeatedMessages:
                await client.delete_message(msg)
        except Exception as e:
            await GearbotLogging.logToModChannel("Exception: {} while trying to delete the messages".format(str(e)))

    #LOG SPAMMED MESSAGE IN LOGGING CHANNEL
        if(Variables.MOD_LOG_CHANNEL != None):
            await GearbotLogging.logToModChannel("{} is spamming a message similar to: ```{}```(in {})".format(message.author.mention, message.content, message.channel))
