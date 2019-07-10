import asyncio
import datetime
import io
import os

import discord

from Util import Utils, GearbotLogging, Translator, Emoji

archive_counter = 0

async def archive_purge(bot, guild_id, messages):
    global archive_counter
    archive_counter += 1
    channel = bot.get_channel(list(messages.values())[0].channel)
    out = f"purged at {datetime.datetime.now()} from {channel.name}\n"
    out += await pack_messages(messages.values())
    buffer = io.BytesIO()
    buffer.write(out.encode())
    GearbotLogging.log_to(guild_id, 'purged_log', count=len(messages), channel=channel.mention, file=(buffer, "Purged messages archive.txt"))

async def pack_messages(messages):
    out = ""
    for message in messages:
        name = await Utils.username(message.author, clean=False)
        out += f"{discord.Object(message.messageid).created_at} {message.server} - {message.channel} - {message.messageid} | {name} ({message.author}) | {message.content} | {(', '.join(attachment.url if hasattr(attachment, 'url') else attachment for attachment in message.attachments))}\r\n"
    return out

async def ship_messages(ctx, messages, t, filename="Message archive"):
    if len(messages) > 0:
        global archive_counter
        archive_counter += 1
        message_list = dict()
        for message in messages:
            message_list[message.messageid] = message
        messages = []
        for mid, message in sorted(message_list.items()):
            messages.append(message)
        out = await pack_messages(messages)
        buffer = io.BytesIO()
        buffer.write(out.encode())
        buffer.seek(0)
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('archived_count', ctx, count=len(messages))}", file=discord.File(fp=buffer, filename=f"{filename}.txt"))
    else:
        await ctx.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate(f'archive_empty_{t}', ctx)}")