import collections
import time
from collections import namedtuple
import datetime

from disnake import Object, HTTPException, MessageType, AllowedMentions
from disnake.utils import time_snowflake

from Util import Translator, Emoji, Archive, GearbotLogging
from database import DBUtils
from database.DBUtils import fakeLoggedMessage
from database.DatabaseConnector import LoggedMessage

Message = namedtuple("Message", "messageid author content channel server attachments type pinned reply_to")



attachment = namedtuple("attachment", "id name")

async def get_message_data(bot, message_id):
    message = None
    if not Object(message_id).created_at <= datetime.datetime.utcfromtimestamp(time.time() - 1 * 60).replace(tzinfo=datetime.timezone.utc):
        parts = await bot.redis_pool.hgetall(f"messages:{message_id}")
        if len(parts) == 7:
            reply = int(parts["reply"])
            message = Message(message_id, int(parts["author"]), parts["content"], int(parts["channel"]), int(parts["server"]), [attachment(a.split("/")[0], a.split("/")[1]) for a in parts["attachments"].split("|")] if len(parts["attachments"]) > 0 else [], type=int(parts["type"]) if "type" in parts else None, pinned=parts["pinned"] == '1', reply_to=reply if reply != 0 else None)
    if message is None:
        message = await LoggedMessage.get_or_none(messageid = message_id).prefetch_related("attachments")
    return message

async def insert_message(bot, message, redis=True):
    message_type = message.type
    if message_type == MessageType.default:
        message_type = None
    else:
        if not isinstance(message_type, int):
            message_type = message_type.value
    if redis:
        pipe = bot.redis_pool.pipeline()
        is_reply = message.reference is not None and message.reference.channel_id == message.channel.id
        pipe.hmset_dict(f"messages:{message.id}", author=message.author.id, content=message.content,
                         channel=message.channel.id, server=message.guild.id, pinned=1 if message.pinned else 0, attachments='|'.join((f"{str(a.id)}/{str(a.filename)}" for a in message.attachments)), reply=message.reference.message_id if is_reply else 0)
        if message_type is not None:
            pipe.hmset_dict(f"messages:{message.id}", type=message_type)
        pipe.expire(f"messages:{message.id}", 1*60)
        await pipe.execute()
    await DBUtils.insert_message(message)

async def update_message(bot, message_id, content, pinned):
    if not Object(message_id).created_at <= datetime.datetime.utcfromtimestamp(time.time() - 1 * 60).replace(tzinfo=datetime.timezone.utc):
        pipe = bot.redis_pool.pipeline()
        pipe.hmset_dict(f"messages:{message_id}", content=content)
        pipe.hmset_dict(f"messages:{message_id}", pinned=(1 if pinned else 0))
        await pipe.execute()
    if message_id in DBUtils.batch:
        old = DBUtils.batch[message_id]
        DBUtils.batch[message_id] = fakeLoggedMessage(message_id, content, old.author, old.channel, old.server, old.type, pinned, old.attachments)
    elif message_id > time_snowflake(datetime.datetime.utcfromtimestamp(time.time() - 60*60*24*7*6).replace(tzinfo=datetime.timezone.utc)):
        await LoggedMessage.filter(messageid=message_id).update(content=content, pinned=pinned)

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


async def send_to(destination, emoji, message, translate=True, embed=None, attachment=None, **kwargs):
    translated = Translator.translate(message, destination.guild, **kwargs) if translate else message
    return await destination.send(f"{Emoji.get_chat_emoji(emoji)} {translated}", embed=embed, allowed_mentions=AllowedMentions(everyone=False, users=True, roles=False), file=attachment)

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
    return f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
