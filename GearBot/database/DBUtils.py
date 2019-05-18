from discord import MessageType
from peewee import IntegrityError

from database.DatabaseConnector import LoggedMessage, LoggedAttachment


def insert_message(message):

    try:
        message_type = message.type

        if message_type == MessageType.default:
            message_type = None
        else:
            message_type = message_type.value
        logged = LoggedMessage.create(messageid=message.id, content=message.content,
                                   author=message.author.id,
                                   channel=message.channel.id, server=message.guild.id,
                                   type=message_type)
        for a in message.attachments:
            LoggedAttachment.create(id=a.id, url=a.url,
                                       isImage=(a.width is not None or a.width is 0),
                                       messageid=message.id)
    except IntegrityError:
        pass
    return logged