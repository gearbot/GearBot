import asyncio
import random
import time
from datetime import datetime

import discord
import aiohttp
from discord.ext import commands
from discord.ext.commands import clean_content, BadArgument

from Cogs.BaseCog import BaseCog
from Util import Configuration, Pages, HelpGenerator, Emoji, Translator, GearbotLogging, Converters, MessageUtils

class Fun(BaseCog):

    def __init__(self, bot):
        super().__init__(bot, {
            "min": 0,
            "max": 6,
            "required": 0,
            "commands": {}
        })
        if Configuration.get_master_var("APEX_KEY", "0") is "0":
            bot.unload_extension("Cogs." + "Fun")

    @commands.command()
    async def apexstats(self, ctx, platform: Converters.ApexPlatform, *, username):
        """about_apexstats"""
        url = "https://public-api.tracker.gg/apex/v1/standard/profile/" + platform + "/" + (username)
        async with self.bot.aiosession.get(url, headers=headers) as resp:
            if resp.status == 404:
                await MessageUtils.send_to(ctx, "NO", "apexstats_user_not_found")
                return
            elif not resp.status == 200:
                await MessageUtils.send_to(ctx, "NO", "apexstats_api_error")
                return
            else:
                responsejson = await resp.json()
                embed = discord.Embed(colour=discord.Colour(0x00cea2), timestamp=datetime.utcfromtimestamp(time.time()))
                embed.add_field(name=Translator.translate('apexstats_username', ctx), value=responsejson["data"]["metadata"]["platformUserHandle"])
                for stat_type in responsejson["data"]["stats"]:
                    type_key_name = stat_type["metadata"]["key"]
                    type_key_value = stat_type["displayValue"]
                    embed.add_field(name=Translator.translate(f'apexstats_key_{type_key_name}', ctx), value=type_key_value)
                await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(Fun(bot))
