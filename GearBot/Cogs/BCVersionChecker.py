import asyncio
import datetime
import time
import traceback
from concurrent.futures import CancelledError

import aiohttp
import discord
from discord.ext import commands

from Util import GearbotLogging, VersionInfo, Permissioncheckers


class BCVersionChecker:
    critical = False
    cog_perm = 0

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.BC_VERSION_LIST = {}
        self.BCC_VERSION_LIST = {}
        self.running = True
        self.force = False
        self.infoCache = {
            "BuildCraft": {},
            "BuildCraftCompat": {}
        }
        self.bot.loop.create_task(versionChecker(self))

    def __unload(self):
        #cleanup
        self.running = False

    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx, True)

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

    @commands.command()
    @commands.bot_has_permissions(manage_roles=True)
    @Permissioncheckers.devOnly()
    async def request_testing(self, ctx:commands.Context, roleName):
        """Make a role pingable for announcements"""
        role = discord.utils.find(lambda r: r.name == roleName, ctx.guild.roles)
        if role is None:
            await ctx.send("Unable to find that role")
        else:
            await role.edit(mentionable=True)
            await ctx.send("Role is now mentionable and awaiting your announcement")

            def check(message:discord.Message):
                return role in message.role_mentions
            until = datetime.datetime.now() + datetime.timedelta(minutes=1)

            done = False
            while not done:
                try:
                    message:discord.Message = await self.bot.wait_for('message', check=check, timeout=(until - datetime.datetime.now()).seconds)
                    if message.author == ctx.author:
                        await message.pin()
                        done = True
                    else:
                        await message.delete()
                        await message.channel.send(f"{message.author.mention}: You where not authorized to mention that role, please do not try that again")
                except:
                    await ctx.send("Time ran out, role is now no longer mentionable")
                    done = True
            await role.edit(mentionable=False)


def setup(bot):
    bot.add_cog(BCVersionChecker(bot))

async def versionChecker(checkcog:BCVersionChecker):
    GearbotLogging.info("Started BC version checking background task")
    session:aiohttp.ClientSession = checkcog.bot.aiosession
    reply:aiohttp.ClientResponse
    lastUpdate = 0
    while checkcog.running:
        try:
            async with session.get('https://www.mod-buildcraft.com/build_info_full/last_change.txt') as reply:
                stamp = await reply.text()
                stamp = int(stamp[:-1])
                if stamp > lastUpdate:
                    GearbotLogging.info("New BC version somewhere!")
                    lastUpdate = stamp
                    checkcog.BC_VERSION_LIST = await getList(session, "BuildCraft")
                    checkcog.BCC_VERSION_LIST = await getList(session, "BuildCraftCompat")
                    highestMC = VersionInfo.getLatest(checkcog.BC_VERSION_LIST.keys())
                    latestBC = VersionInfo.getLatest(checkcog.BC_VERSION_LIST[highestMC])
                    generalID = 309218657798455298
                    channel:discord.TextChannel = checkcog.bot.get_channel(generalID)
                    if channel is not None and latestBC not in channel.topic:
                        info = await checkcog.getVersionDetails("BuildCraft", latestBC)
                        newTopic = f"General discussions about BuildCraft.\n" \
                                   f"Latest version: {latestBC}\n" \
                                   f"Full changelog and download: {info['blog_entry']}"
                        await channel.edit(topic=newTopic)
                    pass
                pass
        except CancelledError:
            pass  # bot shutdown
        except Exception as ex:
            checkcog.bot.errors = checkcog.bot.errors + 1
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
            await GearbotLogging.logToBotlog(embed=embed)
        for i in range(1,60):
            if checkcog.force or not checkcog.running:
                break
            await asyncio.sleep(10)

    GearbotLogging.info("BC version checking background task terminated")


async def getList(session, link):
    async with session.get(f"https://www.mod-buildcraft.com/build_info_full/{link}/versions.json") as reply:
        list = await reply.json()
        if "unknown" in list.keys():
            del list["unknown"]
        return list