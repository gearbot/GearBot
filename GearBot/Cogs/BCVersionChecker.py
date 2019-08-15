import asyncio
import datetime
import hashlib
import time
import traceback
from concurrent.futures import CancelledError

import aiohttp
import discord
from discord import Embed, File
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import GearbotLogging, VersionInfo, Permissioncheckers, Configuration, Utils, Emoji, Pages


class BCVersionChecker(BaseCog):

    def __init__(self, bot):
        super().__init__(bot, self.__class__.__name__)

        self.BC_VERSION_LIST = {}
        self.BCC_VERSION_LIST = {}
        self.running = True
        self.force = False
        self.infoCache = {
            "BuildCraft": {},
            "BuildCraftCompat": {}
        }
        self.bot.loop.create_task(updater(self))

    def cog_unload(self):
        #cleanup
        self.running = False


    @commands.command()
    @Permissioncheckers.bc_only()
    async def latest(self, ctx:commands.Context, version=None):
        if version is None:
            version = VersionInfo.getLatest(self.BC_VERSION_LIST.keys())
        if version not in self.BC_VERSION_LIST.keys():
            await ctx.send(f"Sorry but `{version}` does not seem to be a valid MC version that has BuildCraft releases.")
        else:
            async with ctx.typing():
                latestBC = VersionInfo.getLatest(self.BC_VERSION_LIST[version])
                latestBCinfo = await self.getVersionDetails("BuildCraft", latestBC)

                info = f"Buildcraft {latestBC}:\n[Changelog](https://www.mod-buildcraft.com/pages/buildinfo/BuildCraft/changelog/{latestBC}.html) | [Blog]({latestBCinfo['blog_entry'] if 'blog_entry' in latestBCinfo else 'https://www.mod-buildcraft.com'}) | [Direct download]({latestBCinfo['downloads']['main']})"
                if version in self.BCC_VERSION_LIST.keys():
                    latestBCC = VersionInfo.getLatest(self.BCC_VERSION_LIST[version])
                    latestBCCinfo = await self.getVersionDetails("BuildCraftCompat", latestBCC)
                    info = f"{info}\n\nBuildcraft Compat {latestBCC}:\n[Changelog](https://www.mod-buildcraft.com/pages/buildinfo/BuildCraftCompat/changelog/{latestBCC}.html) | [Blog]({latestBCCinfo['blog_entry'] if 'blog_entry' in latestBCCinfo else 'https://www.mod-buildcraft.com'}) | [Direct download]({latestBCCinfo['downloads']['main']})"

                embed = discord.Embed(colour=discord.Colour(0x54d5ff), timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                      description=info)
                embed.set_author(name=f"BuildCraft releases for {version}", url="https://www.mod-buildcraft.com/pages/download.html", icon_url="https://i.imgur.com/YKGkDDZ.png")
                await ctx.send(embed=embed)


    async def getVersionDetails(self, mod, version):
        if not version in self.infoCache[mod].keys():
            session: aiohttp.ClientSession = self.bot.aiosession
            async with session.get(f'https://www.mod-buildcraft.com/build_info_full/{mod}/{version}.json') as reply:
                info = await reply.json()
                self.infoCache[mod][version] = info
        return self.infoCache[mod][version]

    @commands.command()
    @commands.is_owner()
    async def cleancache(self, ctx):
        """Reset the cache"""
        self.infoCache = {
            "BuildCraft": {},
            "BuildCraftCompat": {}
        }
        await ctx.send("Cache cleaned")

    # @commands.command()
    # @commands.bot_has_permissions(manage_roles=True)
    # @Permissioncheckers.devOnly()
    # async def request_testing(self, ctx:commands.Context, roleName):
    #     """Make a role pingable for announcements"""
    #     role = discord.utils.find(lambda r: r.name == roleName, ctx.guild.roles)
    #     if role is None:
    #         await ctx.send("Unable to find that role")
    #     else:
    #         await role.edit(mentionable=True)
    #         await ctx.send("Role is now mentionable and awaiting your announcement")
    #
    #         def check(message:discord.Message):
    #             return role in message.role_mentions
    #         until = datetime.datetime.now() + datetime.timedelta(minutes=1)
    #
    #         done = False
    #         while not done:
    #             try:
    #                 message:discord.Message = await self.bot.wait_for('message', check=check, timeout=(until - datetime.datetime.now()).seconds)
    #                 if message.author == ctx.author:
    #                     await message.pin()
    #                     done = True
    #                 else:
    #                     await message.delete()
    #                     await message.channel.send(f"{message.author.mention}: You where not authorized to mention that role, please do not try that again")
    #             except:
    #                 await ctx.send("Time ran out, role is now no longer mentionable")
    #                 done = True
    #         await role.edit(mentionable=False)


def setup(bot):
    bot.add_cog(BCVersionChecker(bot))

async def updater(cog:BCVersionChecker):
    GearbotLogging.info("Started BC version checking background task")
    session:aiohttp.ClientSession = cog.bot.aiosession
    lastUpdate = 0
    while cog.running:
        try:
            # check for a newer bc version
            async with session.get('https://www.mod-buildcraft.com/build_info_full/last_change.txt') as reply:
                stamp = await reply.text()
                stamp = int(stamp[:-1])
                if stamp > lastUpdate:
                    GearbotLogging.info("New BC version somewhere!")
                    lastUpdate = stamp
                    cog.BC_VERSION_LIST = await getList(session, "BuildCraft")
                    cog.BCC_VERSION_LIST = await getList(session, "BuildCraftCompat")
                    highestMC = VersionInfo.getLatest(cog.BC_VERSION_LIST.keys())
                    latestBC = VersionInfo.getLatest(cog.BC_VERSION_LIST[highestMC])
                    generalID = 309218657798455298
                    channel:discord.TextChannel = cog.bot.get_channel(generalID)
                    old_latest = Configuration.get_persistent_var("latest_bc", "0.0.0")
                    Configuration.set_persistent_var("latest_bc", latestBC) # save already so we don't get stuck and keep trying over and over if something goes wrong
                    if channel is not None and latestBC != old_latest:
                        GearbotLogging.info(f"New BuildCraft version found: {latestBC}")
                        notify_channel = cog.bot.get_channel(349517224320565258)
                        await notify_channel.send(f"{Emoji.get_chat_emoji('WRENCH')} New BuildCraft version detected ({latestBC})")
                        GearbotLogging.info(f"Fetching metadata for BuildCraft {latestBC}")
                        message = await notify_channel.send(f"{Emoji.get_chat_emoji('REFRESH')} Fetching metadata...")
                        info = await cog.getVersionDetails("BuildCraft", latestBC)
                        GearbotLogging.info(f"Metadata acquired: {info}")
                        await message.edit(content=f"{Emoji.get_chat_emoji('YES')} Metadata acquired")
                        if 'blog_entry' in info:
                            message = await notify_channel.send(f"{Emoji.get_chat_emoji('REFRESH')} Updating general topic...")
                            newTopic = f"General discussions about BuildCraft.\n" \
                                f"Latest version: {latestBC}\n" \
                                f"Full changelog and download: {info['blog_entry']}"
                            await channel.edit(topic=newTopic)
                            await message.edit(content=f"{Emoji.get_chat_emoji('YES')} Topic updated")
                        else:
                            notify_channel.send(f"{Emoji.get_chat_emoji('WARNING')} No blog post data found, notifying <@180057061353193472>")

                        message = await notify_channel.send(f"{Emoji.get_chat_emoji('REFRESH')} Uploading files to CurseForge...")
                        code, output, errors = await Utils.execute(f'cd BuildCraft/uploader && gradle curseforge -Pnew_version="{latestBC}"')
                        GearbotLogging.info(f"Upload to CF complete\n)------stdout------\n{output}\n------stderr------\n{errors}")
                        if code is 0:
                            content = f"{Emoji.get_chat_emoji('YES')} All archives successfully uploaded"
                            await message.edit(content=content)
                        else:
                            content = f"{Emoji.get_chat_emoji('NO')} Upload failed with code {code}, notifying <@106354106196570112>"
                            await notify_channel.send(content)

            # update FAQs if needed
            async with session.get('https://mod-buildcraft.com/website_src/faq.md') as reply:
                data = await reply.text()
                h = hashlib.md5(data.encode('utf-8')).hexdigest()
                old = Configuration.get_persistent_var("BCFAQ", "")
                channel = cog.bot.get_channel(361557801492938762)  # FAQs
                if channel is not None and h != old:
                    Configuration.set_persistent_var("BCFAQ", h)
                    #clean the old stuff
                    await channel.purge()

                    #send banner
                    with open("BuildCraft/FAQs.png", "rb") as file:
                        await channel.send(file=File(file, filename="FAQs.png"))
                    #send content
                    out = ""
                    parts = [d.strip("#").strip() for d in data.split("##")[1:]]
                    for part in parts:
                        lines = part.splitlines()
                        content = '\n'.join(lines[1:])
                        out += f"**```{lines[0].strip()}```**{content}\n"
                    for page in Pages.paginate(out, max_chars=2048 ,max_lines=50):
                        embed = Embed(description=page)
                        await channel.send(embed=embed)



                pass
        except CancelledError:
            pass  # bot shutdown
        except Exception as ex:
            cog.bot.errors = cog.bot.errors + 1
            GearbotLogging.error("Something went wrong in the BC version checker task")
            GearbotLogging.error(traceback.format_exc())
            embed = discord.Embed(colour=discord.Colour(0xff0000),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_author(name="Something went wrong in the BC version checker task:")
            embed.add_field(name="Exception", value=str(ex))
            v = ""
            for line in traceback.format_exc().splitlines():
                if len(v) + len(line) >= 1024:
                    embed.add_field(name="Stacktrace", value=v)
                    v = ""
                v = f"{v}\n{line}"
            if len(v) > 0:
                embed.add_field(name="Stacktrace", value=v)
            await GearbotLogging.bot_log(embed=embed)
        for i in range(1,60):
            if cog.force or not cog.running:
                break
            await asyncio.sleep(10)

    GearbotLogging.info("BC version checking background task terminated")


async def getList(session, link):
    async with session.get(f"https://www.mod-buildcraft.com/build_info_full/{link}/versions.json") as reply:
        list = await reply.json()
        if "unknown" in list.keys():
            del list["unknown"]
        return list