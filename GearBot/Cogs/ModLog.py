import asyncio
import collections
import datetime
import time

import discord
from discord import AuditLogAction
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent
from peewee import IntegrityError

from Util import GearbotLogging, Configuration, Utils, Archive, Emoji, Translator, InfractionUtils
from database.DatabaseConnector import LoggedMessage, LoggedAttachment


class ModLog:

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        self.running = True
        self.cache_message = None
        self.to_cache = []
        self.cache_start = 0
        self.bot.loop.create_task(self.prep())
        self.bot.loop.create_task(cache_task(self))

    def __unload(self):
        self.running = False

    @staticmethod
    def is_enabled(guild_id, log_type):
        return Configuration.get_var(guild_id, log_type)

    async def buildCache(self, guild: discord.Guild, limit=500, startup=False):
        GearbotLogging.info(f"Populating modlog with missed messages during downtime for {guild.name} ({guild.id}).")
        newCount = 0
        editCount = 0
        count = 0
        for channel in guild.text_channels:
            if channel.permissions_for(guild.get_member(self.bot.user.id)).read_messages:
                logged_messages = LoggedMessage.select().where(LoggedMessage.channel == channel.id).order_by(
                    LoggedMessage.messageid.desc()).limit(limit * 1.5)
                messages = dict()
                for message in logged_messages:
                    messages[message.messageid] = message
                async for message in channel.history(limit=limit, reverse=False,
                                                     before=self.cache_message if startup else None):
                    if not self.running:
                        GearbotLogging.info("Cog unloaded while still building cache, aborting.")
                        return
                    if message.author == self.bot.user:
                        continue
                    if message.id not in messages.keys():
                        try:
                            LoggedMessage.create(messageid=message.id, author=message.author.id,
                                                 content=message.content, timestamp=message.created_at.timestamp(),
                                                 channel=channel.id, server=channel.guild.id)
                            for a in message.attachments:
                                LoggedAttachment.create(id=a.id, url=a.url,
                                                        isImage=(a.width is not None or a.width is 0),
                                                        messageid=message.id)
                            newCount = newCount + 1
                        except IntegrityError:
                            # somehow we didn't fetch enough messages, did someone set off a nuke in the channel?
                            logged = LoggedMessage.get(messageid=message.id)
                            if logged.content != message.content:
                                logged.content = message.content
                                logged.save()
                                editCount = editCount + 1
                    else:
                        logged = messages[message.id]
                        if logged.content != message.content:
                            logged.content = message.content
                            logged.save()
                            editCount = editCount + 1
                    count = count + 1
                    if count % 75 is 0:
                        await asyncio.sleep(0)
        GearbotLogging.info(
            f"Discovered {newCount} new messages and {editCount} edited in {guild.name} (checked {count})")

    async def prep(self):
        self.cache_message = await GearbotLogging.bot_log(
            f"{Emoji.get_chat_emoji('REFRESH')} Validating modlog cache")
        self.to_cache = []
        for guild in self.bot.guilds:
            if self.is_enabled(guild.id, "EDIT_LOGS") is not 0:
                self.to_cache.append(guild)
        for i in range(min(3, len(self.bot.guilds))):
            self.bot.loop.create_task(self.startup_cache())
        self.cache_start = time.perf_counter()

    async def startup_cache(self):
        await self.bot.change_presence(activity=discord.Activity(type=3, name='the gears turn'), status="idle")
        while self.to_cache is not None:
            if len(self.to_cache) > 0:
                guild = self.to_cache.pop()
                await self.buildCache(guild, startup=True)
                await asyncio.sleep(0)
            else:
                self.to_cache = None
                minutes, seconds = divmod(round(time.perf_counter() - self.cache_start), 60)
                await self.cache_message.edit(
                    content=f"{Emoji.get_chat_emoji('YES')} Modlog cache validation completed in {minutes} minutes, {seconds} seconds")
                await self.bot.change_presence(activity=discord.Activity(type=3, name='the gears turn'))

    async def on_message(self, message: discord.Message):
        if not hasattr(message.channel, "guild") or message.channel.guild is None:
            return
        if self.is_enabled(message.guild.id, "EDIT_LOGS"):
            LoggedMessage.create(messageid=message.id, author=message.author.id, content=message.content,
                                 timestamp=message.created_at.timestamp(), channel=message.channel.id,
                                 server=message.guild.id)
            for a in message.attachments:
                LoggedAttachment.create(id=a.id, url=a.url, isImage=(a.width is not None or a.width is 0),
                                        messageid=message.id)

    async def on_raw_message_delete(self, data: RawMessageDeleteEvent):
        message = LoggedMessage.get_or_none(messageid=data.message_id)
        if message is not None and self.is_enabled(message.guild.id, "EDIT_LOGS"):
            guild = self.bot.get_guild(message.server)
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            if not hasUser or user.id in Configuration.get_var(guild.id, "IGNORED_USERS") or user.id == guild.me.id:
                return
            attachments = LoggedAttachment.select().where(LoggedAttachment.messageid == data.message_id)
            embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                  description=message.content)
            embed.set_author(name=user.name if hasUser else message.author,
                             icon_url=user.avatar_url if hasUser else EmptyEmbed)
            channel = self.bot.get_channel(message.channel)
            embed.set_footer(text=f"Sent in #{channel.name}")
            if len(attachments) > 0:
                embed.add_field(name=Translator.translate('attachment_link', guild),
                                value="\n".join(attachment.url for attachment in attachments))
            name = Utils.clean_user(user) if hasUser else str(message.author)
            await GearbotLogging.log_to(guild.id, "EDIT_LOGS",
                                        f":wastebasket: {Translator.translate('message_removed', guild.id, name=name, user_id=user.id if hasUser else 'WEBHOOK', channel=channel.mention)}",
                                        embed=embed)

    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        if event.data["channel_id"] == Configuration.get_master_var("BOT_LOG_CHANNEL"):
            return
        message = LoggedMessage.get_or_none(messageid=event.message_id)
        if message is not None and "content" in event.data and self.is_enabled(message.server, "EDIT_LOGS"):
            channel: discord.TextChannel = self.bot.get_channel(int(event.data["channel_id"]))
            if channel.guild is None:
                return
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            if message.content == event.data["content"]:
                # prob just pinned
                return
            if message.content is None or message.content == "":
                message.content = f"<{Translator.translate('no_content', channel.guild.id)}>"
            after = event.data["content"]
            if after is None or after == "":
                after = f"<{Translator.translate('no_content', channel.guild.id)}>"
            if not (hasUser and user.id in Configuration.get_var(channel.guild.id,
                                                                 "IGNORED_USERS") or user.id == channel.guild.me.id):
                embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()))
                embed.set_author(name=user.name if hasUser else message.author,
                                 icon_url=user.avatar_url if hasUser else EmptyEmbed)
                embed.set_footer(
                    text=Translator.translate('sent_in', channel.guild.id, channel=f"#{channel.name}"))
                embed.add_field(name=Translator.translate('before', channel.guild.id),
                                value=Utils.trim_message(message.content, 1024), inline=False)
                embed.add_field(name=Translator.translate('after', channel.guild.id),
                                value=Utils.trim_message(after, 1024), inline=False)
                await GearbotLogging.log_to(channel.guild.id, "EDIT_LOGS",
                                                              f":pencil: {Translator.translate('edit_logging', channel.guild.id, user=Utils.clean_user(user), user_id=user.id, channel=channel.mention)}",
                                            embed=embed)
            message.content = event.data["content"]
            message.save()

    async def on_member_join(self, member: discord.Member):
        if self.is_enabled(member.guild.id, "JOIN_LOGS"):
            dif = (datetime.datetime.utcnow() - member.created_at)
            minutes, seconds = divmod(dif.days * 86400 + dif.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            age = (Translator.translate('days', member.guild.id,
                                        days=dif.days)) if dif.days > 0 else Translator.translate('hours',
                                                                                                  member.guild.id,
                                                                                                  hours=hours,
                                                                                                  minutes=minutes)
            await GearbotLogging.log_to(member.guild.id, "JOIN_LOGS"
                                                         f"{Emoji.get_chat_emoji('JOIN')} {Translator.translate('join_logging', member.guild.id, user=Utils.clean_user(member), user_id=member.id, age=age)}")

    async def on_member_remove(self, member: discord.Member):
        if member.id == self.bot.user.id: return
        exits = self.bot.data["forced_exits"]
        if member.id in exits:
            exits.remove(member.id)
            return
        if member.guild.me.guild_permissions.view_audit_log and self.is_enabled(member.guild.id, "MOD_ACTIONS"):
            try:
                async for entry in member.guild.audit_logs(action=AuditLogAction.kick, limit=2):
                    if member.joined_at > entry.created_at:
                        break
                    if entry.target == member:
                        if entry.reason is None:
                            reason = Translator.translate("no_reason", member.guild.id)
                        else:
                            reason = entry.reason
                        InfractionUtils.add_infraction(member.guild.id, entry.target.id, entry.user.id, "Kick", reason)
                        await GearbotLogging.log_to(member.guild.id, "MOD_ACTIONS"
                                                                     f":boot: {Translator.translate('kick_log', member.guild.id, user=Utils.clean_user(member), user_id=member.id, moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id, reason=reason)}")
                        return
            except discord.Forbidden:
                permissions = member.guild.me.guild_permissions
                perm_info = ", ".join(f"{name}: {value}" for name, value in permissions)
                await GearbotLogging.bot_log(
                    f"{Emoji.get_chat_emoji('WARNING')} Tried to fetch audit log for {member.guild.name} ({member.guild.id}) but got denied even though it said i have access, guild permissions: ```{perm_info}```")

        if self.is_enabled(member.guild.id, "JOIN_LOGS"):
            await GearbotLogging.log_to(member.guild.id, "JOIN_LOGS",
                                        f"{Emoji.get_chat_emoji ('LEAVE')} {Translator.translate('leave_logging', member.guild.id, user=Utils.clean_user(member), user_id=member.id)}")

    async def on_member_ban(self, guild, user):
        if user.id == self.bot.user.id: return
        if user.id in self.bot.data["forced_exits"] or not self.is_enabled(guild.id, "MOD_ACTIONS"):
            return
        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(action=AuditLogAction.ban, limit=2):
                if entry.target == user:
                    if entry.reason is None:
                        reason = Translator.translate("no_reason", guild.id)
                    else:
                        reason = entry.reason
                    InfractionUtils.add_infraction(guild.id, entry.target.id, entry.user.id, "Ban",
                                                   "No reason given." if entry.reason is None else entry.reason)
                    await GearbotLogging.log_to(guild.id, "MOD_ACTIONS",
                                                f":door: {Translator.translate('ban_log', guild.id, user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id, reason=reason)}")
                    return
        await GearbotLogging.log_to(guild.id, "MOD_ACTIONS",
                                    f":door: {Translator.translate('manual_ban_log', guild.id, user=Utils.clean_user(user), user_id=user.id)}")
        self.bot.data["forced_exits"].append(user.id)

    async def on_member_unban(self, guild, user):
        if user.id in self.bot.data["unbans"] or not self.is_enabled(guild.id, "MOD_ACTIONS"):
            return
        else:
            if guild.me.guild_permissions.view_audit_log:
                async for entry in guild.audit_logs(action=AuditLogAction.unban, limit=2):
                    if entry.target == user:
                        InfractionUtils.add_infraction(guild.id, entry.target.id, entry.user.id, "Unban",
                                                       "Manual unban")
                        await GearbotLogging.log_to(guild.id, "MOD_ACTIONS",
                                                    f":door: {Translator.translate('unban_log', guild.id, user=Utils.clean_user(user), user_id=user.id, moderator=entry.user, moderator_id=entry.user.id, reason='Manual unban')}")
                        return
            await GearbotLogging.log_to(guild.id, "MOD_ACTIONS",
                                        f":door: {Translator.translate('manual_unban_log', guild.id, user=Utils.clean_user(user), user_id=user.id)}")

    async def on_member_update(self, before, after):
        guild = before.guild
        audit_log = guild.me.guild_permissions.view_audit_log
        # nickname changes
        if self.is_enabled(guild.id, "NAME_CHANGES"):
            if (before.nick != after.nick and
                    after.nick != before.nick):
                name = Utils.clean_user(after)
                before_clean = "" if before.nick is None else Utils.clean(before.nick)
                after_clean = "" if after.nick is None else Utils.clean(after.nick)
                entry = None
                if audit_log:
                    async for e in guild.audit_logs(action=discord.AuditLogAction.member_update, limit=25):
                        if e.target.id == before.id and before.nick == e.changes.before.nick and hasattr(e.changes.before, "nick") and hasattr(e.changes.after, "nick") and after.nick == e.changes.after.nick:
                            entry = e
                if before.nick is None:
                    type = "added"
                elif after.nick is None:
                    type = "removed"
                else:
                    type = "changed"
                mod_name = ""
                mod_id = ""
                if entry is None:
                    actor = "unknown"
                elif entry.target.id == entry.user.id:
                    actor = "own"
                else:
                    mod_name = Utils.clean_user(entry.user)
                    mod_id = entry.user.id
                    actor = "mod"
                await GearbotLogging.log_to(guild.id, "NAME_CHANGES",
                                            f"{Emoji.get_chat_emoji('NICKTAG')} {Translator.translate(f'{actor}_nickname_{type}', guild, user=name, user_id=before.id, before=before_clean, after=after_clean, moderator=mod_name, moderator_id=mod_id)}")
            # username changes
            elif (before.name != after.name and
                  after.name != before.name):
                before_clean_name = Utils.clean_user(before)
                after_clean_name = Utils.clean_user(after)
                await GearbotLogging.log_to(guild.id, "NAME_CHANGES",
                                            f"{Emoji.get_chat_emoji('NAMETAG')} {Translator.translate('username_changed', guild, after=after_clean_name, before=before_clean_name, user_id=after.id)}")
        # role changes
        if self.is_enabled(guild.id, "ROLE_CHANGES"):
            if len(before.roles) != len(after.roles):
                log_message = ""
                removed = []
                added = []
                for role in before.roles:
                    if role not in after.roles:
                        removed.append(role)

                for role in after.roles:
                    if role not in before.roles:
                        added.append(role)

                entry = None
                if audit_log:
                    async for e in guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=25):
                        if e.target.id == before.id and hasattr(e.changes.before, "roles") and hasattr(e.changes.after, "roles") and all(
                                role in e.changes.before.roles for role in removed) and all(
                            role in e.changes.after.roles for role in added):
                            entry = e
                if entry is not None:
                    removed = entry.changes.before.roles
                    added = entry.changes.after.roles
                    for role in removed:
                        log_message += f"{Emoji.get_chat_emoji('ROLE_REMOVE')} {Translator.translate('role_removed_by', guild, role=role.name, user=Utils.clean_user(entry.target), user_id=entry.target.id, moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id)}\n"
                    for role in added:
                        log_message += f"{Emoji.get_chat_emoji('ROLE_ADD')} {Translator.translate('role_added_by', guild, role=role.name, user=Utils.clean_user(entry.target), user_id=entry.target.id, moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id)}\n"
                else:
                    for role in removed:
                        log_message += f"{Emoji.get_chat_emoji('ROLE_REMOVE')} {Translator.translate('role_removed', guild, role=role.name, user=Utils.clean_user(before), user_id=before.id)}\n"
                    for role in added:
                        log_message += f"{Emoji.get_chat_emoji('ROLE_ADD')} {Translator.translate('role_added', guild, role=role.name, user=Utils.clean_user(before), user_id=before.id)}\n"

                if log_message != "":
                    await GearbotLogging.log_to(guild.id, "ROLE_CHANGES", log_message)

    async def on_raw_bulk_message_delete(self, event: discord.RawBulkMessageDeleteEvent):
        if self.is_enabled(event.guild_id, "EDIT_LOGS"):
            message_list = dict()
            for mid in event.message_ids:
                message = LoggedMessage.get_or_none(LoggedMessage.messageid == mid)
                if message is not None:
                    message_list[mid] = message
            if len(message_list) > 0:
                await Archive.archive_purge(self.bot, event.guild_id,
                                            collections.OrderedDict(sorted(message_list.items())))

    async def on_command_completion(self, ctx):
        if self.is_enabled(ctx.guild.id, "COMMAND_EXECUTED"):
            clean_content = await commands.clean_content(fix_channel_mentions=True).convert(ctx, ctx.message.content)
            await GearbotLogging.log_to(ctx.guild.id, "COMMAND_EXECUTED", f"{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_used', ctx, user=ctx.author, user_id=ctx.author.id, channel=ctx.message.channel.mention, command=clean_content)}")


async def cache_task(modlog: ModLog):
    GearbotLogging.info("Started modlog background task.")
    while modlog.running:
        if len(modlog.bot.to_cache) > 0:
            ctx = modlog.bot.to_cache.pop(0)
            await modlog.buildCache(ctx.guild)
            await ctx.send("Caching complete.")
        await asyncio.sleep(1)
    GearbotLogging.info("modlog background task terminated.")


def setup(bot):
    bot.add_cog(ModLog(bot))
