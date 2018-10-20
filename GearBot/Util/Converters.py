import re

import discord
from discord.ext import commands
from discord.ext.commands import UserConverter

from Util import Utils, Configuration


def clean(text):
    return text.replace("@", "@\u200b").replace("`", "")


class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            entity = await ctx.guild.get_ban(await DiscordUser().convert(ctx, argument))
        except discord.NotFound:
            raise commands.BadArgument("Not a valid previously-banned member.")
        return entity

ID_MATCHER = re.compile("<@!?([0-9]+)>")

class DiscordUser(commands.Converter):
    async def convert(self, ctx, argument):
        user = None
        match = ID_MATCHER.match(argument)
        if match is not None:
            argument = match.group(1)
        try:
            user = await UserConverter().convert(ctx, argument)
        except commands.BadArgument:
            try:
                user = await Utils.get_user(int(argument, base=10))
            except ValueError:
                pass

        if user is None:
            raise commands.BadArgument(f"Unable to convert '{Utils.clean_name(argument)}' to a userid")
        return user

class UserID(commands.Converter):
    async def convert(self, ctx, argument):
        return (await DiscordUser().convert(ctx, argument)).id

EMOJI_MATCHER = re.compile('<a*:([^:]+):(?:[0-9]+)>')

class Reason(commands.Converter):
    async def convert(self, ctx, argument):
        for match in EMOJI_MATCHER.finditer(argument):
            argument = argument.replace(match.group(0), f":{match.group(1)}:")
        return argument

class Duration(commands.Converter):
    async def convert(self, ctx, argument):
        if argument.lower() not in ["week", "weeks", "day", "days", "hour", "hours", "minute", "minutes", "second", "seconds", "w", "d", "h", "m", "s"]:
            raise commands.BadArgument("Invalid duration, valid identifiers: week(s), day(s), hour(s), minute(s), second(s)")
        return argument

class PotentialID(commands.Converter):
    async def convert(self, ctx, argument):
        match = ID_MATCHER.match(argument)
        if match is not None:
            argument = match.group(1)
        try:
            argument = int(argument)
        except ValueError:
            raise commands.BadArgument("Not a potential userid")
        else:
            return argument


CHANNEL_ID_MATCHER = re.compile("<#([0-9]+)>")

class LoggingChannel(commands.Converter):
    async def convert(self, ctx, argument):
        channels = Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
        match = CHANNEL_ID_MATCHER.match(argument)
        if match is not None:
            argument = match.group(1)
        if argument not in channels:
            raise commands.BadArgument("Not an configured logging channel")
        return argument


class RoleMode(commands.Converter):
    async def convert(self, ctx, argument):
        argument = argument.lower()
        options = [
            "alphabetic",
            "hierarchy",
        ]
        if argument in options:
            return argument
        raise commands.BadArgument(f"Unknown mode, valid modes: {', '.join(options)}")
