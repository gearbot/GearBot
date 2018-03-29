import asyncio
import datetime
import time

import discord
from discord.embeds import EmptyEmbed
from discord.ext import commands

from Util import GearbotLogging, Configuration, Permissioncheckers
from database.DatabaseConnector import LoggedMessage


class ModLog:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx:commands.Context):
        return Permissioncheckers.isServerAdmin(ctx)

    @commands.group()
    async def logging(self, ctx:commands.Context):
        pass

    @logging.group()
    async def minor(self, ctx:commands.Context):
        pass

    @minor.command()
    async def setChannel(self, ctx:commands.Context, channel:discord.TextChannel):
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages and permissions.embed_links:
            old = Configuration.getConfigVar(ctx.guild.id, "MINOR_LOGS")
            Configuration.setConfigVar(ctx.guild.id, "MINOR_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for minor logs")
            if old == 0:
                await ctx.send(f"Caching recent messages for logging...")
                await self.buildCache(ctx.guild)
                await ctx.send("Caching complete")
        else:
            await ctx.send(f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages and embed_links)")

    @minor.command()
    async def disable(self, ctx:commands.Context):
        Configuration.setConfigVar(ctx.guild.id, "MINOR_LOGS", 0)


    @logging.group()
    async def join(self, ctx:commands.Context):
        pass

    @join.command()
    async def setChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for join logs")
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages)")

    @join.command()
    async def disable(self, ctx: commands.Context):
        Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", 0)

    @logging.group()
    async def moderation(self, ctx: commands.Context):
        pass

    @moderation.command()
    async def setChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for mod logs")
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages)")

    @moderation.command()
    async def disable(self, ctx: commands.Context):
        Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", 0)

    async def buildCache(self, guild:discord.Guild):
        start = time.perf_counter()
        GearbotLogging.info(f"Populating modlog with missed messages during downtime for {guild.name} ({guild.id})")
        newCount = 0
        editCount = 0
        count = 0
        for channel in guild.text_channels:
            if channel.permissions_for(guild.get_member(self.bot.user.id)).read_messages:
                async for message in channel.history(limit=250, reverse=False):
                    if message.author == self.bot.user or message.content is None or message.content is "":
                        continue
                    logged = LoggedMessage.get_or_none(messageid=message.id)
                    if logged is None:
                        LoggedMessage.create(messageid=message.id, author=message.author.id,
                                                                  content=message.content)
                        newCount = newCount + 1
                    elif logged.content != message.content:
                        logged.content = message.content
                        logged.save()
                        editCount = editCount + 1
                    count = count + 1
                    if count % 20:
                        await asyncio.sleep(0)
        GearbotLogging.info(f"Discovered {newCount} new messages and {editCount} edited in {guild.name} (checked {count}) in {time.perf_counter() - start }s")

    async def on_ready(self):
        for guild in self.bot.guilds:
            if Configuration.getConfigVar(guild.id, "MINOR_LOGS") is not 0:
                await self.buildCache(guild)

    async def on_message(self, message: discord.Message):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        if Configuration.getConfigVar(message.guild.id, "MINOR_LOGS") is 0 or message.author == self.bot.user or message.content is None or message.content is "":
            return
        LoggedMessage.create(messageid=message.id, author=message.author.id, content=message.content)


    async def on_raw_message_delete(self, message_id, channel_id):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        message = LoggedMessage.get_or_none(messageid=message_id)
        if message is not None:
            channel: discord.TextChannel = self.bot.get_channel(channel_id)
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            channelid = Configuration.getConfigVar(channel.guild.id, "MINOR_LOGS")
            if channelid is not 0:
                logChannel:discord.TextChannel = self.bot.get_channel(channelid)
                if logChannel is not None:
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                          description=message.content)
                    embed.set_author(name=user.name if hasUser else message.author, icon_url=user.avatar_url if hasUser else EmptyEmbed)
                    embed.set_footer(text=f"Send in #{channel.name}")
                    await logChannel.send(f":wastebasket: Message by {user.name} (`{user.id}`) in {channel.mention} has been removed", embed=embed)

    async def on_raw_message_edit(self, message_id, data):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        message = LoggedMessage.get_or_none(messageid=message_id)
        if message is not None and "content" in data:
            channel: discord.TextChannel = self.bot.get_channel(int(data["channel_id"]))
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            channelid = Configuration.getConfigVar(channel.guild.id, "MINOR_LOGS")
            if channelid is not 0:
                logChannel: discord.TextChannel = self.bot.get_channel(channelid)
                if logChannel is not None:
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                          description=message.content)
                    embed.set_author(name=user.name if hasUser else message.author,
                                     icon_url=user.avatar_url if hasUser else EmptyEmbed)
                    embed.set_footer(text=f"Send in #{channel.name}")
                    embed.add_field(name="Before", value=message.content, inline=False)
                    embed.add_field(name="After", value=data["content"], inline=False)
                    await logChannel.send(
                        f":pencil: Message by {user.name} (`{user.id}`) in {channel.mention} has been edited",
                        embed=embed)
                    message.content = data["content"]
                    message.save()

    async def on_member_join(self, member:discord.Member):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        channelid = Configuration.getConfigVar(member.guild.id, "JOIN_LOGS")
        if channelid is not 0:
            logChannel:discord.TextChannel = self.bot.get_channel(channelid)
            if logChannel is not None:
                dif = (datetime.datetime.now() - member.created_at)
                age = (f"{dif.days} days") if dif.days > 0 else f"{dif.hour} hours, {dif.min} mins"
                await logChannel.send(f":inbox_tray: {member.display_name}#{member.discriminator} (`{member.id}`) has joined, account created {age} ago")

    async def on_member_remove(self, member:discord.Member):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        channelid = Configuration.getConfigVar(member.guild.id, "JOIN_LOGS")
        if channelid is not 0:
            logChannel: discord.TextChannel = self.bot.get_channel(channelid)
            if logChannel is not None:
                await logChannel.send(f":outbox_tray: {member.display_name}#{member.discriminator} (`{member.id}`) has left the server")



def setup(bot):
    bot.add_cog(ModLog(bot))