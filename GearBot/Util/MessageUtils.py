import collections
import time
from collections import namedtuple
from datetime import datetime

from discord import Object

from Util import Translator, Emoji, Archive
from database.DatabaseConnector import LoggedMessage, LoggedAttachment

Message = namedtuple("Message", "messageid author content channel server")

def is_cache_enabled(bot):
    return bot.redis_pool is not None

async def get_message_data(bot, message_id):
    message = None
    if is_cache_enabled(bot) and not Object(message_id).created_at <= datetime.utcfromtimestamp(time.time() - 5 * 60):
        parts = await bot.redis_pool.hgetall(message_id)
        if len(parts) > 0:
            message = Message(message_id, int(parts["author"]), parts["content"], int(parts["channel"]), int(parts["server"]))
    if message is None:
        message = LoggedMessage.get_or_none(LoggedMessage.messageid == message_id)
    return message

async def insert_message(bot, message):
    if is_cache_enabled(bot):
        pipe = bot.redis_pool.pipeline()
        pipe.hmset_dict(message.id, author=message.author.id, content=message.content,
                         channel=message.channel.id, server=message.guild.id)
        pipe.expire(message.id, 5*60+2)
        await pipe.execute()
    LoggedMessage.create(messageid=message.id, author=message.author.id, content=message.content,
                         channel=message.channel.id, server=message.guild.id)
    for a in message.attachments:
        LoggedAttachment.create(id=a.id, url=a.url, isImage=(a.width is not None or a.width is 0),
                                messageid=message.id)

async def update_message(bot, message_id, content):
    if is_cache_enabled(bot) and not Object(message_id).created_at <= datetime.utcfromtimestamp(time.time() - 5 * 60):
        await bot.redis_pool.hmset_dict(message_id, content=content)
    LoggedMessage.update(content=content).where(LoggedMessage.messageid == message_id)

def assemble(destination, emoji, message, translate=True, **kwargs):
    translated = Translator.translate(message, destination, **kwargs) if translate else message
    return f"{Emoji.get_chat_emoji(emoji)} {translated}"

async def archive_purge(bot, id_list, guild_id):
    message_list = dict()
    for mid in id_list:
        message = await get_message_data(bot, mid)
        if message is not None:
            message_list[mid] = message
    if len(message_list) > 0:
        await Archive.archive_purge(bot, guild_id,
                                    collections.OrderedDict(sorted(message_list.items())))


async def send_to(destination, emoji, message, delete_after=None, translate=True, **kwargs):
    translated = Translator.translate(message, destination.guild, **kwargs) if translate else message
    return await destination.send(f"{Emoji.get_chat_emoji(emoji)} {translated}", delete_after=delete_after)