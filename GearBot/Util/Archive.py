import datetime
import os

import discord

from Util import Utils, GearbotLogging
from database.DatabaseConnector import LoggedAttachment


async def archive(bot, guild_id, messages):
    out = ""
    for mid, message in messages.items():
        name = await Utils.username(message.author)
        out += (
            f"{datetime.datetime.fromtimestamp(message.timestamp)} {guild_id} - {message.channel} - {message.messageid} | {name} ({message.author}) | {message.content} | {', '.join(attachment.url for attachment in LoggedAttachment.select().where(LoggedAttachment.messageid == message.messageid))}\n")

    filename = f"purged at {datetime.datetime.now()}.txt".replace(":", "-")
    if out != "":
        with open(filename, "w", encoding="utf-8") as file:
            file.write(out)
        await GearbotLogging.log_to_minor_log(bot.get_guild(guild_id), file=discord.File(filename))
        os.remove(filename)