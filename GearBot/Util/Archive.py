import datetime
import os

import discord

from Util import Utils, GearbotLogging, Translator, Emoji
from database.DatabaseConnector import LoggedAttachment

archive_counter = 0

async def archive_purge(bot, guild_id, messages):
    global archive_counter
    archive_counter += 1
    channel = bot.get_channel(list(messages.values())[0].channel)
    out = f"purged at {datetime.datetime.now()} from {channel.name}\n"
    out += await pack_messages(messages.values())
    filename = f"Purged messages archive {archive_counter}.txt"
    with open(filename, "w", encoding="utf-8") as file:
        file.write(out)
    with open (filename, "rb") as file:
        await GearbotLogging.log_to(guild_id, "EDIT_LOGS", message=Translator.translate('purged_log', guild_id, count=len(messages), channel=channel.mention), file=discord.File(file, "Purged messages archive.txt"))
    os.remove(filename)

async def pack_messages(messages):
    out = ""
    for message in messages:
        name = await Utils.username(message.author)
        out += f"{datetime.datetime.fromtimestamp(message.timestamp)} {message.server} - {message.channel} - {message.messageid} | {name} ({message.author}) | {message.content} | {', '.join(attachment.url for attachment in LoggedAttachment.select().where(LoggedAttachment.messageid == message.messageid))}\n"
    return out

async def ship_messages(ctx, messages, filename="Message archive"):
    if len(messages) > 0:
        global archive_counter
        archive_counter += 1
        real_name = f"{filename} {archive_counter}.txt"
        message_list = dict()
        for message in messages:
            message_list[message.messageid] = message
        messages = []
        for mid, message in sorted(message_list.items()):
            messages.append(message)
        out = await pack_messages(messages)
        with open(real_name, "w", encoding="utf-8") as file:
            file.write(out)
        with open(real_name, "rb") as file:
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('archived_count', ctx, count=len(messages))}", file=discord.File(file, f"{filename}.txt"))
        os.remove(real_name)
    else:
        await ctx.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('archive_empty', ctx)}")