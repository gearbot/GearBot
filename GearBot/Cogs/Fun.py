import asyncio
import re
import time
from datetime import datetime
import xml.etree.ElementTree as ET


import discord
from discord.ext import commands
from tortoise.exceptions import DoesNotExist


from Cogs.BaseCog import BaseCog
from database.DatabaseConnector import BrawlhallaUser
from Util import Configuration, MessageUtils, Translator, Utils
from Util.Converters import ApexPlatform
from Util.JumboGenerator import JumboGenerator

from Util import Confirmation


STEAM_PROFILE_URL = re.compile("https://steamcommunity.com/id/\w+/?$")

class Fun(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)
        self.brawlhalla_rate_limit_15_minutes = asyncio.Semaphore(180)
        self.brawlhalla_rate_limit_per_second = asyncio.Semaphore(10)


        to_remove = {
            "CAT_KEY": "cat",
            "DOG_KEY": "dog",
            "APEX_KEY": "apexstats",
            "BRAWLHALLA_KEY": "brawlhalla"
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

    async def lock_rate_limits(self):
        await self.brawlhalla_rate_limit_15_minutes.acquire()
        await self.brawlhalla_rate_limit_per_second.acquire()

    async def unlock_rate_limits(self):
        await asyncio.sleep(1)
        self.brawlhalla_rate_limit_15_minutes.release()
        self.brawlhalla_rate_limit_per_second.release()


    @commands.group()
    async def brawlhalla(self, ctx):
        if ctx.invoked_subcommand:
            return
        try:
            link = await BrawlhallaUser.get(discord_id=ctx.author.id)
        except DoesNotExist:
            return await ctx.send(Translator.translate('brawlhalla_no_account_linked', ctx, prefix=Configuration.get_var(ctx.guild.id, 'GENERAL', 'PREFIX')))
        url = f"https://api.brawlhalla.com/player/{link.brawlhalla_id}/stats&api_key={Configuration.get_master_var('BRAWLHALLA_KEY')}"

        try:
            await self.lock_rate_limits()
            async with self.bot.aiosession.get(url) as resp:
                response_json = await resp.json()
                if response_json == {}:
                    await link.delete()
                    return await MessageUtils.send_to(ctx, "NO", "brawlhalla_user_not_found_already_linked")
                else:
                    embed = discord.Embed(timestamp=datetime.utcfromtimestamp(time.time()))
                    if response_json.get("clan"):
                        embed.description = Translator.translate("brawlhalla_stats_for_user_in_clan", ctx,
                                                                 user=await Utils.clean(response_json["name"]),
                                                                 clan=await Utils.clean(response_json["clan"]["clan_name"]))
                    else:
                        embed.description = Translator.translate("brawlhalla_stats_for_user", ctx,
                                                                 user=await Utils.clean(response_json["name"]))
                    embed.add_field(name=Translator.translate("brawlhalla_wins", ctx), value=response_json["wins"])
                    embed.add_field(name=Translator.translate("brawlhalla_games_played", ctx), value=response_json["games"])
                    embed.add_field(name=Translator.translate("brawlhalla_level", ctx), value=response_json["level"])
                    embed.add_field(name=Translator.translate("brawlhalla_legend_count", ctx), value=str(len(response_json["legends"])))
                    await ctx.send(embed=embed)

        finally:
            await self.unlock_rate_limits()

    @brawlhalla.command()
    async def link(self, ctx, steam_id: str):
        if not steam_id.isnumeric():
            if STEAM_PROFILE_URL.match(steam_id):
                async with self.bot.aiosession.get(f"{steam_id}?xml=1") as resp:
                    steam_response = ET.fromstring(await resp.text())
                    if steam_response[0].text.isnumeric():
                        steam_id = steam_response[0].text
                    else:
                        return await MessageUtils.send_to(ctx, "NO", "invalid_steam_id")
            else:
                return await MessageUtils.send_to(ctx, "NO", "invalid_steam_id")
        else:
            if len(steam_id) != 17:
                return await MessageUtils.send_to(ctx, "NO", "invalid_steam_id")

        url = f"https://api.brawlhalla.com/search?steamid={steam_id}&api_key={Configuration.get_master_var('BRAWLHALLA_KEY')}"
        await self.lock_rate_limits()
        try:
            async with self.bot.aiosession.get(url) as resp:
                response_json = await resp.json()
                if not response_json:
                    return await MessageUtils.send_to(ctx, "NO", "not_brawlhalla_player")
                try:
                    link = await BrawlhallaUser.get(discord_id=ctx.author.id)
                except DoesNotExist:
                    await BrawlhallaUser.create(discord_id=ctx.author.id, brawlhalla_id=response_json["brawlhalla_id"])
                    Configuration.get_var(ctx.guild.id, 'GENERAL', 'PREFIX')
                    return await ctx.send(Translator.translate('brawlhalla_account_linked', ctx, prefix=Configuration.get_var(ctx.guild.id, 'GENERAL', 'PREFIX')))
                async def yes():
                    link.brawlhalla_id = response_json["brawlhalla_id"]
                    await link.save()
                    return await MessageUtils.send_to(ctx, "YES", "brawlhalla_new_account_linked")
                await Confirmation.confirm(ctx, Translator.translate("brawlhalla_account_already_linked", ctx), on_yes=yes)
        finally:
            await self.unlock_rate_limits()

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def dog(self, ctx):
        """dog_help"""
        await ctx.trigger_typing()
        future_fact = self.get_json("https://animal.gearbot.rocks/dog/fact")
        key = Configuration.get_master_var("DOG_KEY", "")
        future_dog = self.get_json("https://api.thedogapi.com/v1/images/search?limit=1&size=full", {'x-api-key': key})
        fact_json, dog_json = await asyncio.gather(future_fact, future_dog)
        embed = discord.Embed(description=fact_json["content"])
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
        embed = discord.Embed(description=fact_json["content"])
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
