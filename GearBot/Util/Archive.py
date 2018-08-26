import datetime
import os

import discord

from Util import Utils, GearbotLogging, Translator, Emoji
from database.DatabaseConnector import LoggedAttachment


async def archive_purge(bot, guild_id, messages):
    channel = bot.get_channel(list(messages.values())[0].channel)
    out = f"purged at {datetime.datetime.now()} from {channel.name}\n"
    out += await pack_messages(messages.values())
    filename = "Purged messages archive.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(out)
    await GearbotLogging.log_to_minor_log(bot.get_guild(guild_id), message=Translator.translate('purged_log', guild_id, count=len(messages), channel=channel.mention), file=discord.File(filename))
    os.remove(filename)

async def pack_messages(messages):
    out = ""
    for message in messages:
        name = await Utils.username(message.author)
        out += f"{datetime.datetime.fromtimestamp(message.timestamp)} {message.server} - {message.channel} - {message.messageid} | {name} ({message.author}) | {message.content} | {', '.join(attachment.url for attachment in LoggedAttachment.select().where(LoggedAttachment.messageid == message.messageid))}\n"
    return out

async def ship_messages(ctx, messages, filename="Message archive.txt"):
    if len(messages) > 0:
        out = await pack_messages(messages)
        with open(filename, "w", encoding="utf-8") as file:
            file.write(out)
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('archived_count', ctx, count=len(messages))}", file=discord.File(filename))
        os.remove(filename)
    else:
        await ctx.send(f"{Emoji.get_chat_emoji('WARN')} {Translator.translate('archive_empty', ctx)}")