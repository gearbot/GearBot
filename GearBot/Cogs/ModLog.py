import asyncio
import collections
import datetime
import time

import discord
from discord import AuditLogAction, Role, DMChannel, MessageType
from discord.embeds import EmptyEmbed
from discord.raw_models import RawMessageDeleteEvent, RawMessageUpdateEvent

from Bot.GearBot import GearBot
from Util import GearbotLogging, Configuration, Utils, Archive, Emoji, Translator, InfractionUtils, Features, \
    MessageUtils
from database.DatabaseConnector import LoggedMessage, LoggedAttachment, Infraction


class ModLog:

    def __init__(self, bot):
        self.bot: GearBot = bot
        self.running = True
        self.cache_message = None
        self.to_cache = []
        self.cache_start = 0
        self.bot.loop.create_task(cache_task(self))
        self.clean_collector = dict()

    def __unload(self):
        self.running = False

    async def buildCache(self, guild: discord.Guild, limit=None, startup=False):
        if limit is None:
            limit = 500 if startup else 50
        GearbotLogging.info(f"Populating modlog with missed messages during downtime for {guild.name} ({guild.id}).")
        newCount = 0
        editCount = 0
        count = 0
        no_access = 0
        fetch_times = []
        processing_times = []
        for channel in guild.text_channels:
            permissions = channel.permissions_for(guild.get_member(self.bot.user.id))
            if permissions.read_messages and permissions.read_message_history:

                async for message in channel.history(limit=limit, reverse=False,
                                                     before=self.cache_message if startup else None):
                    processing = time.perf_counter()
                    if not self.running:
                        GearbotLogging.info("Cog unloaded while still building cache, aborting.")
                        return
                    fetch = time.perf_counter()
                    logged = LoggedMessage.get_or_none(messageid=message.id)
                    fetch_times.append(time.perf_counter() - fetch)
                    if logged is None:
                        message_type = message.type
                        if message_type == MessageType.default:
                            message_type = None
                        else:
                            message_type = message_type.value
                        LoggedMessage.create(messageid=message.id, author=message.author.id,
                                             content=message.content,
                                             channel=channel.id, server=channel.guild.id,
                                             type=message_type)
                        for a in message.attachments:
                            LoggedAttachment.create(id=a.id, url=a.url,
                                                    isImage=(a.width is not None or a.width is 0),
                                                    messageid=message.id)
                        newCount = newCount + 1
                    elif message.edited_at is not None:
                        if logged.content != message.content:
                            logged.content = message.content
                            logged.save()
                            editCount = editCount + 1
                    count = count + 1
                    processing_times.append(time.perf_counter() - processing)
                    if count % min(75, int(limit / 2)) is 0:
                        await asyncio.sleep(0)

                await asyncio.sleep(0)
            else:
                no_access += 1
        GearbotLogging.info(
            f"Discovered {newCount} new messages and {editCount} edited in {guild.name} (checked {count})")
        total_fetch_time = sum(fetch_times)
        avg_fetch_time = (total_fetch_time / len(fetch_times)) * 1000
        total_processing = (sum(processing_times)) * 1000
        avg_processing = total_processing / len(processing_times)
        GearbotLogging.info(f"Average fetch time: {avg_fetch_time} (total fetch time: {total_fetch_time})")
        GearbotLogging.info(f"Average processing time: {avg_processing} (total of {total_processing})")
        GearbotLogging.info(f"Was unable to read messages from {no_access} channels")

    async def on_message(self, message: discord.Message):
        if not hasattr(message.channel, "guild") or message.channel.guild is None:
            return
        if Configuration.get_var(message.guild.id, "EDIT_LOGS"):
            await MessageUtils.insert_message(self.bot, message)

    async def on_raw_message_delete(self, data: RawMessageDeleteEvent):
        if data.message_id in self.bot.data["message_deletes"]:
            self.bot.data["message_deletes"].remove(data.message_id)
            return
        c = self.bot.get_channel(data.channel_id)
        if c is None or isinstance(c, DMChannel) or c.guild is None or (not Features.is_logged(c.guild.id, "EDIT_LOGS")) or data.channel_id in Configuration.get_var(c.guild.id,"IGNORED_CHANNELS_OTHER"):
            return
        message = await MessageUtils.get_message_data(self.bot, data.message_id)
        if message is not None:
            if message.channel in self.bot.being_cleaned:
                self.bot.being_cleaned[message.channel].add(data.message_id)
                return
            guild = self.bot.get_guild(message.server)
            user: discord.User = await Utils.get_user(message.author)
            hasUser = user is not None
            if not hasUser or user.id in Configuration.get_var(guild.id, "IGNORED_USERS") or user.id == guild.me.id:
                return
            channel = self.bot.get_channel(message.channel)
            name = Utils.clean_user(user) if hasUser else str(message.author)
            GearbotLogging.log_to(guild.id, "EDIT_LOGS",
                                  f"{Emoji.get_chat_emoji('TRASH')} {Translator.translate('message_removed', guild.id, name=name, user_id=user.id if hasUser else 'WEBHOOK', channel=channel.mention)}")
            type_string = None
            if message.type != None:
                if message.type == MessageType.new_member.value:
                    type_string = Translator.translate('system_message_new_member', guild)
                elif message.type == MessageType.pins_add.value:
                    type_string = Translator.translate('system_message_new_pin', guild)
                else:
                    type_string = Translator.translate('system_message_other', guild)

                type_string = Translator.translate('system_message', guild, type = type_string)
            if Configuration.get_var(channel.guild.id, "EMBED_EDIT_LOGS"):
                embed_content = type_string or message.content

                embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()),
                                      description=embed_content)
                embed.set_author(name=user.name if hasUser else message.author,
                                 icon_url=user.avatar_url if hasUser else EmptyEmbed)

                embed.set_footer(text=Translator.translate('sent_in', guild, channel=channel.name))
                if len(message.attachments) > 0:
                    embed.add_field(name=Translator.translate('attachment_link', guild),
                                    value='\n'.join(attachment.url if hasattr(attachment, 'url') else attachment for attachment in message.attachments))
                GearbotLogging.log_to(guild.id, "EDIT_LOGS", embed=embed)
            else:
                if type_string == None:
                    cleaned_content = await Utils.clean(message.content, channel.guild)
                    GearbotLogging.log_to(guild.id, "EDIT_LOGS", Translator.translate('content', guild, content=cleaned_content), can_stamp=False)
                else:
                    GearbotLogging.log_to(guild.id, "EDIT_LOGS", type_string, can_stamp=False)

                count = 1
                multiple_attachments = len(message.attachments) > 1
                for attachment in message.attachments:
                    attachment_url = attachment.url if hasattr(attachment, 'url') else attachment
                    if multiple_attachments:
                        attachment_str = Translator.translate('attachment_item', guild, num=count, attachment=attachment_url)
                    else:
                        attachment_str = Translator.translate('attachment_single', guild, attachment=attachment_url)

                    GearbotLogging.log_to(guild.id, "EDIT_LOGS", attachment_str, can_stamp=False)
                    count += 1

    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        cid = int(event.data["channel_id"])
        if cid == Configuration.get_master_var("BOT_LOG_CHANNEL"):
            return
        c = self.bot.get_channel(cid)
        if c is None or isinstance(c, DMChannel) or c.guild is None or (not Features.is_logged(c.guild.id, "EDIT_LOGS")) or cid in Configuration.get_var(c.guild.id, "IGNORED_CHANNELS_OTHER"):
            return
        message = await MessageUtils.get_message_data(self.bot, event.message_id)
        if message is not None and "content" in event.data:
            channel: discord.TextChannel = self.bot.get_channel(int(event.data["channel_id"]))
            if channel.guild is None:
                return
            user: discord.User = self.bot.get_user(message.author)
            hasUser = user is not None
            if message.content == event.data["content"]:
                # prob just pinned
                return
            mc = message.content
            if mc is None or mc == "":
                mc = f"<{Translator.translate('no_content', channel.guild.id)}>"
            after = event.data["content"]
            if after is None or after == "":
                after = f"<{Translator.translate('no_content', channel.guild.id)}>"
            if not (hasUser and user.id in Configuration.get_var(channel.guild.id,
                                                                 "IGNORED_USERS") or user.id == channel.guild.me.id):
                GearbotLogging.log_to(channel.guild.id, "EDIT_LOGS",
                                      f"{Emoji.get_chat_emoji('EDIT')} {Translator.translate('edit_logging', channel.guild.id, user=Utils.clean_user(user), user_id=user.id, channel=channel.mention)}")
                if Configuration.get_var(channel.guild.id, "EMBED_EDIT_LOGS"):
                    embed = discord.Embed(timestamp=datetime.datetime.utcfromtimestamp(time.time()))
                    embed.set_author(name=user.name if hasUser else message.author,
                                     icon_url=user.avatar_url if hasUser else EmptyEmbed)
                    embed.set_footer(
                        text=Translator.translate('sent_in', channel.guild.id, channel=f"#{channel.name}"))
                    embed.add_field(name=Translator.translate('before', channel.guild.id),
                                    value=Utils.trim_message(mc, 1024), inline=False)
                    embed.add_field(name=Translator.translate('after', channel.guild.id),
                                    value=Utils.trim_message(after, 1024), inline=False)
                    GearbotLogging.log_to(channel.guild.id, "EDIT_LOGS", embed=embed)
                else:
                    clean_old = await Utils.clean(mc, channel.guild)
                    clean_new = await Utils.clean(after, channel.guild)
                    GearbotLogging.log_to(channel.guild.id, "EDIT_LOGS", f"**Old:** {clean_old}", can_stamp=False)
                    GearbotLogging.log_to(channel.guild.id, "EDIT_LOGS", f"**New:** {clean_new}", can_stamp=False)
            await MessageUtils.update_message(self.bot, event.message_id, after)

    async def on_member_join(self, member: discord.Member):
        if Features.is_logged(member.guild.id, "JOIN_LOGS"):
            dif = (datetime.datetime.utcnow() - member.created_at)
            minutes, seconds = divmod(dif.days * 86400 + dif.seconds, 60)
            hours, minutes = divmod(minutes, 60)
            age = (Translator.translate('days', member.guild.id,
                                        days=dif.days)) if dif.days > 0 else Translator.translate('hours',
                                                                                                  member.guild.id,
                                                                                                  hours=hours,
                                                                                                  minutes=minutes)
            GearbotLogging.log_to(member.guild.id, "JOIN_LOGS",
                                  f"{Emoji.get_chat_emoji('JOIN')} {Translator.translate('join_logging', member.guild.id, user=Utils.clean_user(member), user_id=member.id, age=age)}")

    async def on_member_remove(self, member: discord.Member):
        if member.id == self.bot.user.id: return
        exits = self.bot.data["forced_exits"]
        fid = f"{member.guild.id}-{member.id}"
        if fid in exits:
            exits.remove(fid)
            return
        if member.guild.me.guild_permissions.view_audit_log and Features.is_logged(member.guild.id, "MOD_ACTIONS"):
            try:
                async for entry in member.guild.audit_logs(action=AuditLogAction.kick, limit=25):
                    if member.joined_at is None or member.joined_at > entry.created_at or entry.created_at < datetime.datetime.utcfromtimestamp(
                            time.time() - 30):
                        break
                    if entry.target == member:
                        if entry.reason is None:
                            reason = Translator.translate("no_reason", member.guild.id)
                        else:
                            reason = entry.reason
                        i = InfractionUtils.add_infraction(member.guild.id, entry.target.id, entry.user.id, "Kick", reason,
                                                       active=False)
                        GearbotLogging.log_to(member.guild.id, "MOD_ACTIONS", MessageUtils.assemble(member.guild.id, 'BOOT', 'kick_log', user=Utils.clean_user(member), user_id=member.id, moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id, reason=reason, inf=i.id))
                        return
            except discord.Forbidden:
                permissions = member.guild.me.guild_permissions
                perm_info = ", ".join(f"{name}: {value}" for name, value in permissions)
                await GearbotLogging.bot_log(
                    f"{Emoji.get_chat_emoji('WARNING')} Tried to fetch audit log for {member.guild.name} ({member.guild.id}) but got denied even though it said i have access, guild permissions: ```{perm_info}```")

        if Features.is_logged(member.guild.id, "JOIN_LOGS"):
            GearbotLogging.log_to(member.guild.id, "JOIN_LOGS",
                                  f"{Emoji.get_chat_emoji ('LEAVE')} {Translator.translate('leave_logging', member.guild.id, user=Utils.clean_user(member), user_id=member.id)}")

    async def on_member_ban(self, guild, user):
        if user.id == self.bot.user.id or not Features.is_logged(guild.id, "MOD_ACTIONS"): return
        fid = f"{guild.id}-{user.id}"
        if fid in self.bot.data["forced_exits"]:
            return
        self.bot.data["forced_exits"].add(fid)
        Infraction.update(active=False).where((Infraction.user_id == user.id) &
                                              (Infraction.type == "Unban") &
                                              (Infraction.guild_id == guild.id)).execute()
        await asyncio.sleep(1) # sometimes we get the event before things are in the log for some reason
        limit = datetime.datetime.utcfromtimestamp(time.time() - 60)
        log = await self.find_log(guild, AuditLogAction.ban, lambda e: e.target == user and e.created_at > limit)
        if log is None:
            await asyncio.sleep(1) #is the api having a fit or so?
            #this fails way to often for my liking, alternative is adding a delay but this seems to do the trick for now
            log = await self.find_log(guild, AuditLogAction.ban, lambda e: e.target == user and e.created_at > limit)
        if log is not None:
            if log.reason is None:
                reason = Translator.translate("no_reason", guild.id)
            else:
                reason = log.reason
            i = InfractionUtils.add_infraction(guild.id, log.target.id, log.user.id, "Ban", reason)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", MessageUtils.assemble(guild.id, "BAN", 'ban_log', user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(log.user), moderator_id=log.user.id, reason=reason, inf=i.id))
        else:
            i = InfractionUtils.add_infraction(guild.id, user.id, 0, "Ban", "Manual ban")
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", MessageUtils.assemble(guild.id, "BAN", 'manual_ban_log', user=Utils.clean_user(user), user_id=user.id, inf=i.id))

    async def on_member_unban(self, guild, user):
        fid = f"{guild.id}-{user.id}"
        if fid in self.bot.data["unbans"]:
            self.bot.data["unbans"].remove(fid)
            return
        elif not Features.is_logged(guild.id, "MOD_ACTIONS"):
            return
        Infraction.update(active=False).where((Infraction.user_id == user.id) &
                                              (Infraction.type == "Ban") &
                                              (Infraction.guild_id == guild.id)).execute()

        limit = datetime.datetime.utcfromtimestamp(time.time() - 60)
        log = await self.find_log(guild, AuditLogAction.unban, lambda e: e.target == user and e.created_at > limit)
        if log is None:
            # this fails way to often for my liking, alternative is adding a delay but this seems to do the trick for now
            log = await self.find_log(guild, AuditLogAction.unban, lambda e: e.target == user and e.created_at > limit)
        if log is not None:
            i = InfractionUtils.add_infraction(guild.id, user.id, log.user.id, "Unban", "Manual ban")
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS",
                                  MessageUtils.assemble(guild.id, 'INNOCENT', 'unban_log', user=Utils.clean_user(user),
                                                        user_id=user.id, moderator=log.user,
                                                        moderator_id=log.user.id, reason='Manual unban', inf=i.id))


        else:
            i = InfractionUtils.add_infraction(guild.id, user.id, 0, "Unban", "Manual ban")
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", MessageUtils.assemble(guild.id, 'INNOCENT', 'manual_unban_log',  user=Utils.clean_user(user),user_id=user.id, inf=i.id))

    async def on_member_update(self, before:discord.Member, after):
        guild = before.guild
        # nickname changes
        if Features.is_logged(guild.id, "NAME_CHANGES"):
            if (before.nick != after.nick and
                    after.nick != before.nick):
                name = Utils.clean_user(after)
                before_clean = "" if before.nick is None else Utils.clean_name(before.nick)
                after_clean = "" if after.nick is None else Utils.clean_name(after.nick)
                entry = await self.find_log(guild, AuditLogAction.member_update, lambda e: e.target.id == before.id and hasattr(e.changes.before, "nick") and hasattr(e.changes.after, "nick") and before.nick == e.changes.before.nick and after.nick == e.changes.after.nick and e.created_at > datetime.datetime.utcfromtimestamp(time.time() - 2))
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
                GearbotLogging.log_to(guild.id, "NAME_CHANGES",
                                      f"{Emoji.get_chat_emoji('NICKTAG')} {Translator.translate(f'{actor}_nickname_{type}', guild, user=name, user_id=before.id, before=before_clean, after=after_clean, moderator=mod_name, moderator_id=mod_id)}")

        # role changes
        if Features.is_logged(guild.id, "ROLE_CHANGES"):
            removed = []
            added = []
            for role in before.roles:
               if role not in after.roles:
                    removed.append(role)

            for role in after.roles:
                if role not in before.roles:
                    added.append(role)

            if (len(removed) + len(added)) > 0:
                entry = await self.find_log(guild, AuditLogAction.member_role_update,
                                            lambda e: e.target.id == before.id and hasattr(e.changes.before, "roles") and hasattr(
                                                e.changes.after, "roles") and all(
                                                r in e.changes.before.roles for r in removed) and all(
                                                r in e.changes.after.roles for r in
                                                added) and e.created_at > datetime.datetime.utcfromtimestamp(
                                                time.time() - 1))
                if entry is not None:
                    removed = entry.changes.before.roles
                    added = entry.changes.after.roles
                    for role in removed:
                        GearbotLogging.log_to(guild.id, "ROLE_CHANGES",
                                              f"{Emoji.get_chat_emoji('ROLE_REMOVE')} {Translator.translate('role_removed_by', guild, role=role.name, user=Utils.clean_user(entry.target), user_id=entry.target.id, moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id)}")
                    for role in added:
                        GearbotLogging.log_to(guild.id, "ROLE_CHANGES",
                                              f"{Emoji.get_chat_emoji('ROLE_ADD')} {Translator.translate('role_added_by', guild, role=role.name, user=Utils.clean_user(entry.target), user_id=entry.target.id, moderator=Utils.clean_user(entry.user), moderator_id=entry.user.id)}")
                else:
                    for role in removed:
                        GearbotLogging.log_to(guild.id, "ROLE_CHANGES",
                                              f"{Emoji.get_chat_emoji('ROLE_REMOVE')} {Translator.translate('role_removed', guild, role=role.name, user=Utils.clean_user(before), user_id=before.id)}")
                    for role in added:
                        GearbotLogging.log_to(guild.id, "ROLE_CHANGES",
                                              f"{Emoji.get_chat_emoji('ROLE_ADD')} {Translator.translate('role_added', guild, role=role.name, user=Utils.clean_user(before), user_id=before.id)}")

        # username changes
        if before.name != after.name or before.discriminator != after.discriminator:
            for guild in self.bot.guilds:
                if guild.get_member(before.id) is not None:
                    after_clean_name = Utils.escape_markdown(after)
                    GearbotLogging.log_to(guild.id, "NAME_CHANGES",
                                          f"{Emoji.get_chat_emoji('NAMETAG')} {Translator.translate('username_changed', guild, after_clean=after_clean_name, before=before, user_id=after.id, after=after)}")


    async def on_voice_state_update(self, member, before, after):
        if Features.is_logged(member.guild.id, "VOICE_CHANGES_DETAILED"):
            simple = ["deaf", "mute", "self_mute", "self_deaf", "afk"]
            for s in simple:
                old = getattr(before, s)
                new = getattr(after, s)
                if old != new:
                    key = f"voice_change_{s}_{str(new).lower()}"
                    logging = MessageUtils.assemble(member.guild.id, "VOICE", key, user=Utils.clean_user(member), user_id=member.id)
                    GearbotLogging.log_to(member.guild.id, "VOICE_CHANGES_DETAILED", logging)
        if Features.is_logged(member.guild.id, "VOICE_CHANGES"):
            if before.channel != after.channel:
                parts = dict(user=Utils.clean_user(member), user_id=member.id)
                if before.channel is None:
                    key = "connected_to_voice"
                    parts.update(channel_name=after.channel.name, channel_id=after.channel.id)
                elif after.channel is None:
                    key = "disconnected_voice"
                    parts.update(channel_name=before.channel.name, channel_id=before.channel.id)
                else:
                    key = "moved_voice"
                    parts.update(old_channel_name=before.channel.name, old_channel_id=before.channel.id,
                                 new_channel_name=after.channel.name, new_channel_id=after.channel.id)
                logging = MessageUtils.assemble(member.guild.id, "VOICE", key, **parts)
                GearbotLogging.log_to(member.guild.id, "VOICE_CHANGES", logging)

    async def on_raw_bulk_message_delete(self, event: discord.RawBulkMessageDeleteEvent):
        if Features.is_logged(event.guild_id, "EDIT_LOGS"):
            if event.channel_id in Configuration.get_var(event.guild_id, "IGNORED_CHANNELS_OTHER"):
                return
            if event.channel_id in self.bot.being_cleaned:
                for mid in event.message_ids:
                    self.bot.being_cleaned[event.channel_id].add(mid)
                return
            message_list = dict()
            for mid in event.message_ids:
                message = await MessageUtils.get_message_data(self.bot, mid)
                if message is not None:
                    message_list[mid] = message
            if len(message_list) > 0:
                await Archive.archive_purge(self.bot, event.guild_id,
                                            collections.OrderedDict(sorted(message_list.items())))

    async def on_command_completion(self, ctx):
        if ctx.guild is not None and Features.is_logged(ctx.guild.id, "COMMAND_EXECUTED"):
            logging = f"{Emoji.get_chat_emoji('WRENCH')} {Translator.translate('command_used', ctx, user=ctx.author, user_id=ctx.author.id, channel=ctx.message.channel.mention)} "
            clean_content = await Utils.clean(ctx.message.content, ctx.guild, markdown=False, links=False, emoji=False)
            GearbotLogging.log_to(ctx.guild.id, "COMMAND_EXECUTED", logging,
                                  tag_on=f"``{Utils.trim_message(clean_content, 1994)}``")

    async def on_guild_channel_create(self, channel):
        if not Features.is_logged(channel.guild.id, "CHANNEL_CHANGES"): return
        e = await self.find_log(channel.guild, AuditLogAction.channel_create, lambda e: e.target.id == channel.id)
        if e is not None:
            logging = MessageUtils.assemble(channel.guild.id, "CREATE", "channel_created_by" , channel=channel.name, channel_id=channel.id, person=Utils.clean_user(e.user), person_id=e.user.id)
        else:
            logging = MessageUtils.assemble(channel.guild.id, "CREATE", "channel_created", channel=channel.name, channel_id=channel.id)
        GearbotLogging.log_to(channel.guild.id, "CHANNEL_CHANGES", logging)

    async def on_guild_channel_delete(self, channel):
        if not Features.is_logged(channel.guild.id, "CHANNEL_CHANGES"): return
        e = await self.find_log(channel.guild, AuditLogAction.channel_delete, lambda e: e.target.id == channel.id)
        if e is not None:
            logging = MessageUtils.assemble(channel.guild.id, "DELETE", "channel_deleted_by", channel=channel.name, channel_id=channel.id, person=Utils.clean_user(e.user), person_id=e.user.id)
        else:
            logging = MessageUtils.assemble(channel.guild.id, "DELETE", "channel_delete", channel=channel.name, channel_id=channel.id)
        GearbotLogging.log_to(channel.guild.id, "CHANNEL_CHANGES", logging)

    async def on_guild_channel_update(self, before, after):
        if not Features.is_logged(before.guild.id, "CHANNEL_CHANGES") or before.id in Configuration.get_var(before.guild.id, "IGNORED_CHANNELS_CHANGES"): return
        await self.handle_simple_changes(before, after, "channel_update_simple", "CHANNEL_CHANGES",
                                         AuditLogAction.channel_update,
                                         ["name", "category", "nsfw", "slowmode_delay", "topic", "bitrate",
                                          "user_limit"])

        # checking overrides
        old_overrides = dict()
        for target, override in before.overwrites:
            old_overrides[target] = override

        new_overrides = dict()
        for target, override in after.overwrites:
            new_overrides[target] = override

        for target, override in old_overrides.items():
            if target in new_overrides:
                # still exists, check for modifications
                a_override = new_overrides[target]
                if override._values != a_override._values:
                    # something changed
                    for perm, value in override:
                        new_value = getattr(a_override, perm)
                        if value != new_value:
                            parts = dict(before=self.prep_override(value), after=self.prep_override(new_value),
                                         permission=perm, channel=Utils.escape_markdown(after), channel_id=after.id,
                                         target_name=Utils.escape_markdown(str(target)), target_id=target.id)
                            key = "permission_override_update"

                            def finder(e):
                                if e.target.id == after.id and e.target.id == after.id and e.extra.id == target.id:
                                    before_allowed, before_denied = override.pair()
                                    after_allowed, after_denied = new_overrides[target].pair()
                                    has_allow = hasattr(e.before, "allow")
                                    has_deny = hasattr(e.before, "deny")
                                    if not ( ((has_allow and (before_allowed.value != after_allowed.value) and before_allowed.value == e.before.allow.value and after_allowed.value == e.after.allow.value) or (has_allow == hasattr(e.after, "allow")))
                                                and ((has_deny and (before_denied.value != before_denied.value) and before_denied.value == e.before.deny.value and after_denied.value == e.after.deny.value) or has_deny == hasattr(e.after, "deny"))):
                                        return False
                                    return True
                                return False

                            entry = await self.find_log(after.guild, AuditLogAction.overwrite_update, finder)
                            if isinstance(target, Role):
                                key += "_role"
                            if entry is not None:
                                key += "_by"
                                parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
                            logging = MessageUtils.assemble(after.guild.id, "ALTER", key, **parts)
                            GearbotLogging.log_to(after.guild.id, "CHANNEL_CHANGES", logging)
            else:
                # permission override removed
                key = "permission_override_removed"
                parts = dict(channel=Utils.escape_markdown(after), channel_id=after.id, target_name=Utils.escape_markdown(str(target)), target_id=target.id)

                def finder(e):
                    if e.target.id == after.id and e.extra.id == target.id:
                        before_allowed, before_denied = override.pair()
                        has_allow = hasattr(e.before, "allow")
                        has_deny = hasattr(e.before, "deny")
                        if not ((has_allow and before_allowed.value == e.before.allow.value) or ( (not has_allow) and before_allowed.value is 0)
                            and (has_deny and before_denied.value == e.before.deny.value) or ( (not has_deny) and before_denied.value is 0)):
                            return False
                        return True

                entry = await self.find_log(after.guild, AuditLogAction.overwrite_delete, finder)
                if isinstance(target, Role):
                    key += "_role"
                if entry is not None:
                    key += "_by"
                    parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
                logging = MessageUtils.assemble(after.guild.id, "ALTER", key, **parts)
                GearbotLogging.log_to(after.guild.id, "CHANNEL_CHANGES", logging)

        for target in set(new_overrides.keys()).difference(old_overrides.keys()):
            key = "permission_override_added"
            parts = dict(channel=Utils.escape_markdown(after), channel_id=after.id, target_name=Utils.escape_markdown(str(target)), target_id=target.id)

            def finder(e):
                if e.target.id == after.id and e.extra.id == target.id:
                    after_allowed, after_denied = new_overrides[target].pair()
                    has_allow = hasattr(e.after, "allow")
                    has_deny = hasattr(e.after, "deny")
                    if not ((has_allow and after_allowed.value == e.after.allow.value) or (
                            (not has_allow) and after_allowed.value is 0)
                            and (has_deny and after_denied.value == e.after.deny.value) or (
                                    (not has_deny) and after_denied.value is 0)):
                        return False
                    return True

            entry = await self.find_log(after.guild, AuditLogAction.overwrite_create, finder)
            if isinstance(target, Role):
                key += "_role"
            if entry is not None:
                key += "_by"
                parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
            logging = MessageUtils.assemble(after.guild.id, "ALTER", key, **parts)
            GearbotLogging.log_to(after.guild.id, "CHANNEL_CHANGES", logging)

    async def on_guild_role_create(self, role):
        if not Features.is_logged(role.guild.id, "ROLE_CHANGES"): return
        entry = await self.find_log(role.guild, AuditLogAction.role_create, lambda e: e.target.id == role.id)
        if entry is None:
            logging = MessageUtils.assemble(role.guild.id, "CREATE", "role_created", role=role.name)
        else:
            logging = MessageUtils.assemble(role.guild.id, "CREATE", "role_created_by", role=role.name, person=Utils.clean_user(entry.user), person_id=entry.user.id)
        GearbotLogging.log_to(role.guild.id, "ROLE_CHANGES", logging)

    async def on_guild_role_delete(self, role:discord.Role):
        if not Features.is_logged(role.guild.id, "ROLE_CHANGES"): return
        entry = await self.find_log(role.guild, AuditLogAction.role_delete, lambda e: e.target.id == role.id)
        if entry is None:
            logging = MessageUtils.assemble(role.guild.id, "DELETE", "role_deleted", role=role.name)
        else:
            logging = MessageUtils.assemble(role.guild.id, "DELETE", "role_deleted_by", role=role.name,
                                          person=Utils.clean_user(entry.user), person_id=entry.user.id)
        GearbotLogging.log_to(role.guild.id, "ROLE_CHANGES", logging)


    async def on_guild_role_update(self, before:discord.Role, after):
        if not Features.is_logged(before.guild.id, "ROLE_CHANGES"): return
        await self.handle_simple_changes(before, after, "role_update_simple", "ROLE_CHANGES", AuditLogAction.role_update,  ["name", "color", "hoist", "mentionable"])
        if before.permissions != after.permissions:
            for perm, value in before.permissions:
                av = getattr(after.permissions, perm)
                if av != value:
                    entry = await self.find_log(before.guild, AuditLogAction.role_update,
                                                lambda e: e.target.id == after.id and hasattr(e.before, "permissions") and e.before.permissions == before.permissions and e.after.permissions == after.permissions)
                    key = f"role_update_perm_{'added' if av else 'revoked'}"
                    parts = dict(role=await Utils.clean(after.name), role_id=after.id, perm=perm)
                    if entry is not None:
                        key += "_by"
                        parts.update(person=Utils.clean_user(entry.user), person_id=entry.user.id)
                    logging = MessageUtils.assemble(before.guild.id, "ALTER", key, **parts)
                    GearbotLogging.log_to(after.guild.id, "ROLE_CHANGES", logging)




    async def handle_simple_changes(self, before, after, base_key, log_key, action, attributes):
        for attr in attributes:
            if hasattr(before, attr):
                ba = getattr(before, attr)
                if isinstance(ba, str) and ba.strip() == "":
                    ba = None
                aa = getattr(after, attr)
                if isinstance(aa, str) and aa.strip() == "":
                    aa = None
                key = base_key
                if ba != aa:
                    entry = await self.find_log(before.guild, action,
                                                lambda e: e.target.id == before.id and hasattr(e.changes.before, attr) and getattr(e.changes.before, attr) == ba and getattr(e.changes.after, attr) == aa)
                    parts = dict(before=self.prep_attr(ba), after=self.prep_attr(aa), thing=after, thing_id=after.id, attr=attr)
                    if entry is not None:
                        parts.update(person=entry.user, person_id=entry.user.id)
                        key += "_by"
                    logging = MessageUtils.assemble(before.guild.id, "ALTER", key, **parts)
                    GearbotLogging.log_to(before.guild.id, log_key, logging)



    @staticmethod
    def prep_attr(attr):
        attr = f"\u200b{Utils.trim_message(str(attr), 900)}\u200b"
        if "\n" in attr:
            return f"`{attr}`"
        return attr

    @staticmethod
    def prep_override(value):
        if value is None:
            return "neutral"
        elif value is False:
            return "denied"
        elif value is True:
            return "granted"

    @staticmethod
    async def find_log(guild, action, matcher, check_limit=10):
        entry = None
        if guild.me.guild_permissions.view_audit_log:
            try:
                async for e in guild.audit_logs(action=action, limit=check_limit):
                    if matcher(e):
                        if entry is None or e.id > entry.id:
                            entry = e
            except discord.Forbidden:
                pass
        return entry




async def cache_task(modlog: ModLog):
    GearbotLogging.info("Started modlog background task.")
    while modlog.running:
        if len(modlog.bot.to_cache) > 0:
            ctx = modlog.bot.to_cache.pop(0)
            await modlog.buildCache(ctx.guild, limit=500)
            await ctx.send("Caching complete.")
        await asyncio.sleep(1)
    GearbotLogging.info("modlog background task terminated.")


def setup(bot):
    bot.add_cog(ModLog(bot))
