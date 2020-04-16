import collections
import time
from collections import namedtuple
from datetime import datetime

from discord import Object, HTTPException, MessageType

from Util import Translator, Emoji, Archive, GearbotLogging
from database import DBUtils
from database.DatabaseConnector import LoggedMessage

Message = namedtuple("Message", "messageid author content channel server attachments type pinned")

def is_cache_enabled(bot):
    return bot.redis_pool is not None


attachment = namedtuple("attachment", "id name")

async def get_message_data(bot, message_id):
    message = None
    if is_cache_enabled(bot) and not Object(message_id).created_at <= datetime.utcfromtimestamp(time.time() - 5 * 60):
        parts = await bot.redis_pool.hgetall(f"messages:{message_id}")
        if len(parts) is 6:
            message = Message(message_id, int(parts["author"]), parts["content"], int(parts["channel"]), int(parts["server"]), [attachment(a.split("/")[0], a.split("/")[1]) for a in parts["attachments"].split("|")] if len(parts["attachments"]) > 0 else [], type=int(parts["type"]) if "type" in parts else None, pinned=parts["pinned"] == '1')
    if message is None:
        message = LoggedMessage.get_or_none(LoggedMessage.messageid == message_id)
    return message

async def insert_message(bot, message, redis=True):
    message_type = message.type
    if message_type == MessageType.default:
        message_type = None
    else:
        if not isinstance(message_type, int):
            message_type = message_type.value
    if redis and is_cache_enabled(bot):
        pipe = bot.redis_pool.pipeline()
        pipe.hmset_dict(f"messages:{message.id}", author=message.author.id, content=message.content,
                         channel=message.channel.id, server=message.guild.id, pinned=1 if message.pinned else 0, attachments='|'.join((f"{str(a.id)}/{str(a.filename)}" for a in message.attachments)))
        if message_type is not None:
            pipe.hmset_dict(f"messages:{message.id}", type=message_type)
        pipe.expire(f"messages:{message.id}", 5*60+2)
        await pipe.execute()
    DBUtils.insert_message(message)

async def update_message(bot, message_id, content, pinned):
    if is_cache_enabled(bot) and not Object(message_id).created_at <= datetime.utcfromtimestamp(time.time() - 5 * 60):
        pipe = bot.redis_pool.pipeline()
        pipe.hmset_dict(f"messages:{message_id}", content=content)
        pipe.hmset_dict(f"messages:{message_id}", pinned=(1 if pinned else 0))
        await pipe.execute()
    LoggedMessage.update(content=content, pinned=pinned).where(LoggedMessage.messageid == message_id).execute()

def assemble(destination, emoji, m, translate=True, **kwargs):
    translated = Translator.translate(m, destination, **kwargs) if translate else m
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


async def send_to(destination, emoji, message, delete_after=None, translate=True, embed=None, **kwargs):
    translated = Translator.translate(message, destination.guild, **kwargs) if translate else message
    return await destination.send(f"{Emoji.get_chat_emoji(emoji)} {translated}", delete_after=delete_after, embed=embed)

async def try_edit(message, emoji: str, string_name: str, embed=None, **kwargs):
    translated = Translator.translate(string_name, message.channel, **kwargs)
    try:
        return await message.edit(content=f'{Emoji.get_chat_emoji(emoji)} {translated}', embed=embed)
    except HTTPException:
        return await send_to(message.channel, emoji, string_name, embed=embed, **kwargs)


def day_difference(a, b, location):
    diff = a - b
    return Translator.translate('days_ago', location, days=diff.days, date=a)

def construct_jumplink(guild_id, channel_id, message_id):
    return f"https://discordapp.com/channels/{guild_id}/{channel_id}/{message_id}"
