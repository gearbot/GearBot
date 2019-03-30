import asyncio
import random
import time
from datetime import datetime

import discord
import aiohttp
from discord.ext import commands
from discord.ext.commands import clean_content, BadArgument

from Cogs.BaseCog import BaseCog
from Util import Configuration, Pages, HelpGenerator, Emoji, Translator, Utils, GearbotLogging

class GameStats(BaseCog):

    def __init__(self, bot):
        super().__init__(bot, {
            "min": 0,
            "max": 6,
            "required": 0,
            "commands": {}
        })
        self.session = aiohttp.ClientSession(loop=bot.loop)

    @commands.command()
    async def apexstats(self, ctx, platform, *, username):
        """about_apexstats"""
        if platform is None:
            apexplatform = "5"
        elif platform == "pc":
            apexplatform = "5"
        elif platform == "psn":
            apexplatform = "2"
        elif platform == "xbox":
            apexplatform = "1"
        else:
            await ctx.send(Translator.translate('apexstats_invalid_platform', ctx))
            return
        url = "https://public-api.tracker.gg/apex/v1/standard/profile/" + apexplatform + "/" + (username)
        if not Configuration.get_master_var("APEX_KEY", "0") is "0":
            headers = {"TRN-Api-Key": Configuration.get_master_var("APEX_KEY")}
        else:
            await ctx.send("There is no API key provided by the Administrator of this GearBot stats.")
            return
        async with self.session.get(url, headers=headers) as resp:
            if resp.status == 404:
                await ctx.send(Translator.translate('apexstats_user_not_found', ctx))
                return
            elif not resp.status == 200:
                await ctx.send(Translator.translate('apexstats_api_error', ctx))
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
    bot.add_cog(GameStats(bot))
