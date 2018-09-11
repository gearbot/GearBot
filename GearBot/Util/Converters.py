import re

import discord
from discord.ext import commands

from Util import Utils


class BannedMember(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            entity = await ctx.guild.get_ban(await Utils.get_user(await UserID().convert(ctx, argument)))
        except discord.NotFound:
            raise commands.BadArgument("Not a valid previously-banned member.")
        return entity

ID_MATCHER = re.compile("<@!?([0-9]+)>")

class UserID(commands.Converter):
    async def convert(self, ctx, argument):
        match = ID_MATCHER.match(argument)
        if match is not None:
            argument = match.group(1)
        user = None
        try:
            user = await Utils.get_user(int(argument, base=10))
        except ValueError:
            pass
        if user is None:
            raise commands.BadArgument(f"Unable to convert '{Utils.clean_user(argument)}' to a userid")
        return user.id

EMOJI_MATCHER = re.compile('<a*:([^:]+):(?:[0-9]+)>')

class Reason(commands.Converter):
    async def convert(self, ctx, argument):
        for match in EMOJI_MATCHER.finditer(argument):
            argument = argument.replace(match.group(0), f":{match.group(1)}:")
        return argument