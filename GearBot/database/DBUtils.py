from peewee import IntegrityError

from database.DatabaseConnector import LoggedMessage, LoggedAttachment


def insert_message(message):

    try:
        logged = LoggedMessage.create(messageid=message.id, content=message.content,
                                   author=message.author.id,
                                   channel=message.channel.id, server=message.guild.id)
        for a in message.attachments:
            LoggedAttachment.create(id=a.id, url=a.url,
                                       isImage=(a.width is not None or a.width is 0),
                                       messageid=message.id)
    except IntegrityError as ex:
        pass
    return logged