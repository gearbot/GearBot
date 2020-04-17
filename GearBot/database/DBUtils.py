import time

from discord import MessageType
from peewee import IntegrityError

from Util import GearbotLogging
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


async def insert_message(message):
    try:
        message_type = message.type

        if message_type == MessageType.default:
            message_type = None
        else:
            if not isinstance(message_type, int):
                message_type = message_type.value
        logged = await LoggedMessage.create(messageid=message.id, content=message.content,
                                   author=message.author.id,
                                   channel=message.channel.id, server=message.guild.id,
                                   type=message_type, pinned=message.pinned)
        for a in message.attachments:
            await LoggedAttachment.create(id=a.id, name=a.filename,
                                       isImage=(a.width is not None or a.width is 0),
                                       messageid=message.id)
    except IntegrityError:
        return message
    return logged