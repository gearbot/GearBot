import asyncio
import time
from datetime import datetime

import discord
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import Configuration, MessageUtils, Translator, Utils
from Util.Converters import ApexPlatform
from Util.JumboGenerator import JumboGenerator


class Fun(BaseCog):

    def __init__(self, bot):
        super().__init__(bot, {
            "min": 0,
            "max": 6,
            "required": 0,
            "commands": {}
        })
        to_remove = {
            "CAT_KEY": "cat",
            "DOG_KEY": "dog",
            "APEX_KEY": "apexstats"
        }
        for k, v in to_remove.items():
            if Configuration.get_master_var(k, "0") == "0":
                bot.remove_command(v)

    @commands.command()
    async def apexstats(self, ctx, platform: ApexPlatform, *, username):
        """about_apexstats"""
        headers = {"TRN-Api-Key": Configuration.get_master_var("APEX_KEY")}
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
                embed.add_field(name=Translator.translate('apexstats_username', ctx), value=await Utils.clean(responsejson["data"]["metadata"]["platformUserHandle"]))
                for stat_type in responsejson["data"]["stats"]:
                    type_key_name = stat_type["metadata"]["key"]
                    type_key_value = stat_type["displayValue"]
                    embed.add_field(name=Translator.translate(f'apexstats_key_{type_key_name}', ctx), value=type_key_value)
                await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def dog(self, ctx):
        """dog_help"""
        await ctx.trigger_typing()
        future_fact = self.get_json("https://animal.gearbot.rocks/dog/fact")
        key = Configuration.get_master_var("DOG_KEY", "")
        future_dog = self.get_json("https://api.thedogapi.com/v1/images/search?limit=1&size=full", {'x-api-key': key})
        fact_json, dog_json = await asyncio.gather(future_fact, future_dog)
        embed = discord.Embed(description=fact_json["fact"])
        if key != "":
            embed.set_image(url=dog_json[0]["url"])
        await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def cat(self, ctx):
        """cat_help"""
        await ctx.trigger_typing()
        future_fact = self.get_json("https://animal.gearbot.rocks/cat/fact")
        key = Configuration.get_master_var("CAT_KEY", "")
        future_cat = self.get_json("https://api.thecatapi.com/v1/images/search?limit=1&size=full", {'x-api-key': key})
        fact_json, cat_json = await asyncio.gather(future_fact, future_cat)
        embed = discord.Embed(description=fact_json["fact"])
        if key != "":
            embed.set_image(url=cat_json[0]["url"])
        await ctx.send(embed=embed)

    async def get_json(self, link, headers=None):
            async with self.bot.aiosession.get(link, headers=headers) as reply:
                return await reply.json()


    @commands.command()
    @commands.bot_has_permissions(attach_files=True)
    async def jumbo(self, ctx, *, emojis: str):
        """jumbo_help"""
        await JumboGenerator(ctx, emojis).generate()

def setup(bot):
    bot.add_cog(Fun(bot))
