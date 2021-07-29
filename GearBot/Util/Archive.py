import asyncio
import datetime
import io
import os

import discord
import pytz

from Util import Utils, GearbotLogging, Translator, Emoji, Configuration

archive_counter = 0

async def archive_purge(bot, guild_id, messages):
    global archive_counter
    archive_counter += 1
    channel = bot.get_channel(list(messages.values())[0].channel)
    out = f"purged at {datetime.datetime.utcnow()} from {channel.name}\n"
    out += await pack_messages(messages.values(), guild_id)
    buffer = io.BytesIO()
    buffer.write(out.encode())
    GearbotLogging.log_key(guild_id, 'purged_log', count=len(messages), channel=channel.mention, file=(buffer, "Purged messages archive.txt"))

async def pack_messages(messages, guild_id):
    out = ""
    for message in messages:
        name = await Utils.username(message.author, clean=False)
        reply = ""
        if message.reply_to is not None:
            reply = f" | In reply to https://discord.com/channels/{message.server}/{message.channel}/{message.reply_to}"
        timestamp = datetime.datetime.strftime(discord.Object(message.messageid).created_at.astimezone(pytz.timezone(Configuration.get_var(guild_id, 'GENERAL', 'TIMEZONE'))),'%H:%M:%S')
        out += f"{timestamp} {message.server} - {message.channel} - {message.messageid} | {name} ({message.author}) | {message.content}{reply} | {(', '.join(Utils.assemble_attachment(message.channel, attachment.id, attachment.name) for attachment in message.attachments))}\r\n"
    return out

async def ship_messages(ctx, messages, t, filename="Message archive", filtered=False):
    addendum = ""
    if filtered:
        addendum = f"\n{Emoji.get_chat_emoji('WARNING')} {Translator.translate('archive_message_filtered', ctx)}"
    if len(messages) > 0:
        global archive_counter
        archive_counter += 1
        message_list = dict()
        for message in messages:
            message_list[message.messageid] = message
        messages = []
        for mid, message in sorted(message_list.items()):
            messages.append(message)
        out = await pack_messages(messages, ctx.guild.id)
        buffer = io.BytesIO()
        buffer.write(out.encode())
        buffer.seek(0)

        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('archived_count', ctx, count=len(messages))} {addendum}", file=discord.File(fp=buffer, filename=f"{filename}.txt"))
    else:
        await ctx.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate(f'archive_empty_{t}', ctx)} {addendum}")