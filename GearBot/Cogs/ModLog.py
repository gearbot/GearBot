import asyncio
import datetime
import time

import discord
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent

from Util import GearbotLogging, Configuration, Permissioncheckers, Utils
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


class ModLog:

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.bot.loop.create_task(self.prep())
        self.bot.loop.create_task(cache_task(self))
        self.running = True

    def __unload(self):
        self.running = False

    async def __local_check(self, ctx:commands.Context):
        return Permissioncheckers.isServerAdmin(ctx)

    async def buildCache(self, guild:discord.Guild, limit = 250):
        start = time.perf_counter()
        GearbotLogging.info(f"Populating modlog with missed messages during downtime for {guild.name} ({guild.id})")
        newCount = 0
        editCount = 0
        count = 0
        for channel in guild.text_channels:
            if channel.permissions_for(guild.get_member(self.bot.user.id)).read_messages:
                async for message in channel.history(limit=limit, reverse=False):
                    if not self.running:
                        GearbotLogging.info("Cog unloaded while still building cache, aborting")
                        return
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

    async def prep(self):
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
            if hasUser and user.id in Configuration.getConfigVar(channel.guild.id, "IGNORED_USERS"):
                return
            channelid = Configuration.getConfigVar(channel.guild.id, "MINOR_LOGS")
            if channelid is not 0:
                logChannel:discord.TextChannel = self.bot.get_channel(channelid)
                if logChannel is not None and message.content != None and message.content != "":
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                          description=message.content)
                    embed.set_author(name=user.name if hasUser else message.author, icon_url=user.avatar_url if hasUser else EmptyEmbed)
                    embed.set_footer(text=f"Send in #{channel.name}")
                    await logChannel.send(f":wastebasket: Message by {user.name if hasUser else message.author}#{user.discriminator} (`{user.id}`) in {channel.mention} has been removed", embed=embed)

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
                    embed.add_field(name="Before", value=Utils.trim_message(message.content, 1024), inline=False)
                    embed.add_field(name="After", value=Utils.trim_message(event.data["content"], 1024), inline=False)
                    if not (hasUser and user.id in Configuration.getConfigVar(channel.guild.id, "IGNORED_USERS")):
                        await logChannel.send(f":pencil: Message by {user.name}#{user.discriminator} (`{user.id}`) in {channel.mention} has been edited",
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

    async def on_member_ban(self, guild, user):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        channelid = Configuration.getConfigVar(guild.id, "MOD_LOGS")
        if channelid is not 0:
            logChannel: discord.TextChannel = self.bot.get_channel(channelid)
            if logChannel is not None:
                await logChannel.send(
                    f":rotating_light: {user.name}#{user.discriminator} (`{user.id}`) has been banned from the server.")

    async def on_member_unban(self, guild, user):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        channelid = Configuration.getConfigVar(guild.id, "MOD_LOGS")
        if channelid is not 0:
            logChannel: discord.TextChannel = self.bot.get_channel(channelid)
            if logChannel is not None:
                await logChannel.send(
                    f":rotating_light: {user.name}#{user.discriminator} (`{user.id}`) has been unbanned from the server.")

    def Clean_Name(self, text):
        return text.replace("@","").replace("`","")
        
    async def on_member_update(self, before, after):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        channelid = Configuration.getConfigVar(after.guild.id, "MINOR_LOGS")
        if channelid is not 0:
            logChannel: discord.TextChannel = self.bot.get_channel(channelid)
            if logChannel is not None:
                if (before.nick != after.nick and
                    after.nick != before.nick):
                    after_clean_name = self.Clean_Name(after.name)
                    after_clean_display_name = self.Clean_Name(after.display_name)
                    before_clean_name = self.Clean_Name(after.name)
                    before_clean_display_name = self.Clean_Name(before.display_name)
                    await logChannel.send(
                        f':name_badge: {after_clean_name}#{after.discriminator} (`{after.id}`) has changed nickname from **``\u200b{before_clean_display_name}``** to **``\u200b{after_clean_display_name}``**.'
                    )
                elif (before.name != after.name and
                    after.name != before.name):
                    after_clean_name = self.Clean_Name(after.name)
                    after_clean_display_name = self.Clean_Name(after.display_name)
                    before_clean_name = self.Clean_Name(before.name)
                    before_clean_display_name = self.Clean_Name(before.display_name)
                    await logChannel.send(
                        f':name_badge: {before_clean_name}#{before.discriminator} (`{before.id}`) has changed username from **``\u200b{before_clean_name}``** to **``\u200b{after_clean_name}``**.'
                    )


async def cache_task(modlog:ModLog):
    while not modlog.bot.STARTUP_COMPLETE:
        await asyncio.sleep(1)
    GearbotLogging.info("Started modlog background task")
    while modlog.running:
        if len(modlog.bot.to_cache) > 0:
            ctx = modlog.bot.to_cache.pop(0)
            await modlog.buildCache(ctx.guild)
            await ctx.send("Caching complete")
        await asyncio.sleep(1)
    GearbotLogging.info("modlog background task terminated")



def setup(bot):
    bot.add_cog(ModLog(bot))
