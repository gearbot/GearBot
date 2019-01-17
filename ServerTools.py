import asyncio
import discord
from discord.ext import commands

import GearBot
from Bot import TheRealGearBot
from Util import Permissioncheckers, GearbotLogging, Emoji, Translator, MessageUtils

class ServerTools:
    permissions = {
        "min": 3,
        "max": 6,
        "required": 3
    }
    def __init__(self, bot):
        self.bot: GearBot = bot
        self.handling = set()


    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    @commands.guild_only()       
    @commands.command()
    async def announce(self, ctx: commands.Context, channel:discord.TextChannel, *, message):
        if message != None:
            try:
                await channel.send("{message}") 
            except discord.Forbidden:
                await MessageUtils.send_to(ctx, 'NO', 'announce_invaild_id')
                
def setup(bot):
    bot.add_cog(ServerTools(bot))
