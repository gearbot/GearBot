import asyncio
import discord
from discord.ext import commands
from discord.ext.commands import BadArgument, Greedy, MemberConverter, RoleConverter

import GearBot
from Bot import TheRealGearBot
from Util import Permissioncheckers, Configuration, Utils, GearbotLogging, Pages, Emoji, Translator, \
   Confirmation, MessageUtils
from Util.Converters import DiscordUser, PotentialID, RoleMode, Guild, \
    RangedInt, Message

class ServerTools:
    permissions = {
        "min": 3,
        "max": 6,
        "required": 3
    }
    def __init__(self, bot):
        self.bot: GearBot = bot
        self.running = True
        self.handling = set()

    def __unload(self):
        self.running = False

    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    @commands.guild_only()       
    @commands.command()
    async def announce(self, ctx: commands.Context, channel:discord.TextChannel, *, message):
        if message != None:
            try:
                await channel.send(f"{message}") 
            except discord.Forbidden:
                await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('announce_invaild_id', ctx)}")
def setup(bot):
    bot.add_cog(ServerTools(bot))