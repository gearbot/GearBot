import asyncio
import datetime
import time

import discord
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.ext.commands import BadArgument
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent, RawReactionActionEvent, RawReactionClearEvent

from Cogs.Serveradmin import Serveradmin
from Util import GearbotLogging, Configuration, Permissioncheckers
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


class ModLog:

    def __init__(self, bot):
        self.bot:commands.Bot = bot

    async def __local_check(self, ctx:commands.Context):
        return Permissioncheckers.isServerAdmin(ctx)


    @Serveradmin.configure.command()
    async def minorLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for minor logs (edit/delete)"""
        if channel is None:
            raise BadArgument("Missing channel")
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

    @Serveradmin.disable.command(name="minorLogChannel")
    async def disableMinorLogChannel(self, ctx:commands.Context):
        """Disables minor logs (edit/delete)"""
        Configuration.setConfigVar(ctx.guild.id, "MINOR_LOGS", 0)
        await ctx.send("Minor logs have been dissabled")


    @Serveradmin.configure.command()
    async def joinLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for join/leave logs"""
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for join logs")
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages)")

    @Serveradmin.disable.command(name="joinLogChannel")
    async def disablejoinLogChannel(self, ctx: commands.Context):
        """Disables join/leave logs"""
        Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", 0)
        await ctx.send("Join logs have been dissabled")

    @Serveradmin.configure.command()
    async def modLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for modlogs (mute/kick/ban/...)"""
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for mod logs")
        else:
            await ctx.send(f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages)")

    @Serveradmin.disable.command(name="modLogChannel")
    async def disablemodLogChannel(self, ctx: commands.Context):
        """Disables the modlogs (mute/kick/ban/...)"""
        Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", 0)
        await ctx.send("Mod logs have been dissabled")

    async def buildCache(self, guild:discord.Guild):
        start = time.perf_counter()
        GearbotLogging.info(f"Populating modlog with missed messages during downtime for {guild.name} ({guild.id})")
        newCount = 0
        editCount = 0
        count = 0
        for channel in guild.text_channels:
            if channel.permissions_for(guild.get_member(self.bot.user.id)).read_messages:
                async for message in channel.history(limit=250, reverse=False):
                    if message.author == self.bot.user:
                        continue
                    logged = LoggedMessage.get_or_none(messageid=message.id)
                    if logged is None:
                        LoggedMessage.create(messageid=message.id, author=message.author.id,
                                                              content=message.content, timestamp = message.created_at.timestamp(), channel=channel.id)
                        for a in message.attachments:
                            LoggedAttachment.create(id=a.id, url=a.url, isImage=(a.width is not None or a.width is 0), messageid=message.id)
                        newCount = newCount + 1
                    elif logged.content != message.content:
                        logged.content = message.content
                        logged.save()
                        editCount = editCount + 1
                    count = count + 1
        GearbotLogging.info(f"Discovered {newCount} new messages and {editCount} edited in {guild.name} (checked {count}) in {time.perf_counter() - start }s")

    async def on_ready(self):
        for guild in self.bot.guilds:
            if Configuration.getConfigVar(guild.id, "MINOR_LOGS") is not 0:
                await self.buildCache(guild)

    async def on_message(self, message: discord.Message):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        if not hasattr(message.channel, "guild") or message.channel.guild is None:
            return
        if Configuration.getConfigVar(message.guild.id, "MINOR_LOGS") is 0 or message.author == self.bot.user:
            return
        for a in message.attachments:
            LoggedAttachment.create(id=a.id, url=a.url, isImage=(a.width is not None or a.width is 0), messageid=message.id)
        LoggedMessage.create(messageid=message.id, author=message.author.id, content=message.content, timestamp=message.created_at.timestamp(), channel=message.channel.id)


    async def on_raw_message_delete(self, data:RawMessageDeleteEvent):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        message = LoggedMessage.get_or_none(messageid=data.message_id)
        if message is not None:
            channel: discord.TextChannel = self.bot.get_channel(data.channel_id)
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            channelid = Configuration.getConfigVar(channel.guild.id, "MINOR_LOGS")
            if channelid is not 0:
                logChannel:discord.TextChannel = self.bot.get_channel(channelid)
                if logChannel is not None and message.content != None and message.content != "":
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                          description=message.content)
                    embed.set_author(name=user.name if hasUser else message.author, icon_url=user.avatar_url if hasUser else EmptyEmbed)
                    embed.set_footer(text=f"Send in #{channel.name}")
                    await logChannel.send(f":wastebasket: Message by {user.name if hasUser else message.author} (`{user.id}`) in {channel.mention} has been removed", embed=embed)

    async def on_raw_message_edit(self, event:RawMessageUpdateEvent):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        message = LoggedMessage.get_or_none(messageid=event.message_id)
        if message is not None and "content" in event.data:
            channel: discord.TextChannel = self.bot.get_channel(int(event.data["channel_id"]))
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            channelid = Configuration.getConfigVar(channel.guild.id, "MINOR_LOGS")
            if channelid is not 0:
                logChannel: discord.TextChannel = self.bot.get_channel(channelid)
                if logChannel is not None:
                    if message.content == event.data["content"]:
                        #prob just pinned
                        return
                    if message.content is None or message.content == "":
                        message.content = "<no content>"
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()))
                    embed.set_author(name=user.name if hasUser else message.author,
                                     icon_url=user.avatar_url if hasUser else EmptyEmbed)
                    embed.set_footer(text=f"Send in #{channel.name}")
                    embed.add_field(name="Before", value=message.content, inline=False)
                    embed.add_field(name="After", value=event.data["content"], inline=False)
                    await logChannel.send(
                        f":pencil: Message by {user.name} (`{user.id}`) in {channel.mention} has been edited",
                        embed=embed)
                    message.content = event.data["content"]
                    message.save()

    async def on_member_join(self, member:discord.Member):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        channelid = Configuration.getConfigVar(member.guild.id, "JOIN_LOGS")
        if channelid is not 0:
            logChannel:discord.TextChannel = self.bot.get_channel(channelid)
            if logChannel is not None:
                dif = (datetime.datetime.utcnow() - member.created_at)
                minutes, seconds = divmod(dif.days * 86400 + dif.seconds, 60)
                hours, minutes = divmod(minutes, 60)
                age = (f"{dif.days} days") if dif.days > 0 else f"{hours} hours, {minutes} mins"
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