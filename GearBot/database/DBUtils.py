import time

from discord import MessageType
from peewee import IntegrityError

from Util import GearbotLogging
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


def insert_message(message):
    start = time.perf_counter_ns()
    try:
        message_type = message.type

        if message_type == MessageType.default:
            message_type = None
        else:
            if not isinstance(message_type, int):
                message_type = message_type.value
        logged = LoggedMessage.create(messageid=message.id, content=message.content,
                                   author=message.author.id,
                                   channel=message.channel.id, server=message.guild.id,
                                   type=message_type, pinned=message.pinned)
        for a in message.attachments:
            LoggedAttachment.create(id=a.id, name=a.filename,
                                       isImage=(a.width is not None or a.width is 0),
                                       messageid=message.id)
    except IntegrityError:
        return message
    end = time.perf_counter_ns()
    GearbotLogging.info(f"inserted message into the database in {(end - start) / 1000000} ms")
    return logged