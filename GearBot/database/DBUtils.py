from discord import MessageType

from database.Models import LoggedMessage, LoggedAttachment


async def insert_message(message):

    try:
        message_type = message.type

        if message_type == MessageType.default:
            message_type = None
        else:
            if not isinstance(message_type, int):
                message_type = message_type.value
        logged = await LoggedMessage.create(id=message.id, content=message.content,
                                   author=message.author.id,
                                   channel=message.channel.id, server=message.guild.id,
                                   type=message_type, pinned=message.pinned)

        for a in message.attachments:
            await LoggedAttachment.create(id=a.id, name=a.filename,
                                       isImage=(a.width is not None or a.width is 0), message=logged)
    except Exception as ex:
        raise ex
        # return message
    return logged