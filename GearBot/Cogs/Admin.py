import asyncio
import os
import subprocess
from datetime import datetime
from subprocess import Popen

import discord
from discord.ext import commands

from Util import GearbotLogging, Utils, Configuration


class Admin:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx):
        return await ctx.bot.is_owner(ctx.author)


    @commands.command(hidden=True)
    async def restart(self, ctx):
        """Restarts the bot"""
        await ctx.send("Restarting...")
        await Utils.cleanExit(self.bot, ctx.author.name)

    @commands.command(hidden=True)
    async def upgrade(self, ctx):
        await ctx.send("<:BCWrench:344163417981976578> I'll be right back with new gears! <:woodGear:344163118089240596> <:stoneGear:344163146325295105> <:ironGear:344163170664841216> <:goldGear:344163202684289024> <:diamondGear:344163228101640192>")
        await GearbotLogging.logToBotlog(f"Upgrade initiated by {ctx.author.name}", log=True)
        file = open("upgradeRequest", "w")
        file.write("upgrade requested")
        file.close()
        await self.bot.logout()
        await self.bot.close()
        await asyncio.sleep(11)

    @commands.command()
    async def stats(self, ctx):
        """Operational stats"""
        uptime = datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        days, hours = divmod(hours, 24)
        minutes, seconds = divmod(remainder, 60)
        tacos, remainder = divmod(int(uptime.total_seconds()), 15)
        await ctx.send(
            f"<:gearDiamond:433284297345073153> Gears have been spinning for {days} {'day' if days is 1 else 'days'}, {hours} {'hour' if hours is 1 else 'hours'}, {minutes} {'minute' if minutes is 1 else 'minutes'} and {seconds} {'second' if seconds is 1 else 'seconds'}\n"
            f"<:gearGold:433284297554788352> {self.bot.messageCount} messages have been processed\n"
            f"<:gearIron:433284297563045901> Number of times ks has grinded my gears (causing errors): {self.bot.errors}\n"
            f"<:gearStone:433284297340878849> Numbers of command executed: {self.bot.commandCount}\n"
            f"<:gearWood:433284297336815616> Working in {len(self.bot.guilds)} guilds\n"
            f":taco: About {tacos} tacos could have been produced and eaten in this time\n"
            f"<:todo:433693576036352024> Add more stats")

    @commands.command()
    async def reconnectdb(self, ctx):
        """Disconnect and reconnect the database, for in case it does run away again"""
        self.bot.database_connection.close()
        self.bot.database_connection.connect()
        await ctx.send("Database connection re-established")

    @commands.command()
    async def pull(self, ctx):
        """Pulls from github so an upgrade can be performed without full restart"""
        async with ctx.typing():
            p = Popen(["git pull origin master"], cwd=os.getcwd(), shell=True, stdout=subprocess.PIPE)
            while p.poll() is None:
                await asyncio.sleep(1)
            out, error = p.communicate()
            await ctx.send(f"Pull completed with exit code {p.returncode}```yaml\n{out.decode('utf-8')}```")

    @commands.command()
    async def setstatus(self, ctx, type:int, *, status:str):
        await self.bot.change_presence(activity=discord.Activity(name=status, type=type))
        await ctx.send("Status updated")

    @commands.command()
    async def reloadconfigs(self, ctx:commands.Context):
        async with ctx.typing():
            Configuration.loadGlobalConfig()
            await Configuration.onReady(self.bot)
            await ctx.send("Configs reloaded")

    @commands.command()
    async def serverinfo(self, ctx):
        """Shows information about the current server."""
        guild_features = ", ".join(ctx.guild.features)
        print(guild_features)
        if guild_features == "":
            guild_features = None
        role_list = []
        for i in range(len(ctx.guild.roles)):
            role_list.append(ctx.guild.roles[i].name)
        guild_made = ctx.guild.created_at.strftime("%d-%m-%Y")
        embed = discord.Embed(color=0x7289DA)
        embed.set_thumbnail(url=ctx.guild.icon_url)
        requested_at = ctx.message.created_at.strftime("%d-%m-%Y %I:%M%p")
        embed.set_footer(text=f"Requested by {ctx.author.name} at {requested_at}", icon_url=ctx.author.avatar_url)
        embed.add_field(name="Name", value=ctx.guild.name, inline=True)
        embed.add_field(name="ID", value=ctx.guild.id, inline=True)
        embed.add_field(name="Owner", value=ctx.guild.owner, inline=True)
        embed.add_field(name="Members", value=ctx.guild.member_count, inline=True)
        embed.add_field(name="Text Channels", value=len(ctx.guild.text_channels), inline=True)
        embed.add_field(name="Voice Channels", value=len(ctx.guild.voice_channels), inline=True)
        embed.add_field(name="Total Channels", value=len(ctx.guild.text_channels) + len(ctx.guild.voice_channels),
                        inline=True)
        embed.add_field(name="Created at",
                        value=f"{guild_made} ({(ctx.message.created_at - ctx.guild.created_at).days} days ago)",
                        inline=True)
        embed.add_field(name="VIP Features", value=guild_features, inline=True)
        if ctx.guild.icon_url != "":
            embed.add_field(name="Server Icon URL", value=ctx.guild.icon_url, inline=True)
        embed.add_field(name="Roles", value=", ".join(role_list), inline=True)
        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Admin(bot))