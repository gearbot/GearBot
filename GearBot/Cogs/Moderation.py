import asyncio
import datetime
import time
import traceback
from concurrent.futures import CancelledError

import discord
from discord.ext import commands
from discord.ext.commands import BadArgument, Greedy, MemberConverter

from Util import Permissioncheckers, Configuration, Utils, GearbotLogging, Pages, InfractionUtils, Emoji, Translator, \
    Archive, Confirmation
from Util.Converters import BannedMember, UserID, Reason, Duration, DiscordUser, PotentialID
from database.DatabaseConnector import LoggedMessage


class Moderation:
    permissions = {
        "min": 2,
        "max": 6,
        "required": 2,
        "commands": {
            "userinfo": {"required": 2, "min": 0, "max": 6},
            "serverinfo": {"required": 2, "min": 0, "max": 6},
            "roles": {"required": 2, "min": 0, "max": 6},
        }
    }

    def __init__(self, bot):
        self.bot: commands.Bot = bot
        bot.mutes = self.mutes = Utils.fetch_from_disk("mutes")
        self.running = True
        self.bot.loop.create_task(unmuteTask(self))
        Pages.register("roles", self.roles_init, self.roles_update)
        Pages.register("mass_failures", self._mass_failures_init, self._mass_failures_update)

    def __unload(self):
        Utils.saveToDisk("mutes", self.mutes)
        self.running = False
        Pages.unregister("roles")

    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    async def roles_init(self, ctx):
        pages = self.gen_roles_pages(ctx.guild)
        page = pages[0]
        return f"**{Translator.translate('roles', ctx.guild.id, server_name=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{page}```", None, len(pages) > 1, []

    async def roles_update(self, ctx, message, page_num, action, data):
        pages = self.gen_roles_pages(message.guild)
        page, page_num = Pages.basic_pages(pages, page_num, action)
        return f"**{Translator.translate('roles', message.guild.id, server_name=ctx.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```", None, page_num

    @staticmethod
    def gen_roles_pages(guild: discord.Guild):
        role_list = dict()
        longest_name = 1
        for role in guild.roles:
            role_list[f"{role.name} - {role.id}"] = role
            longest_name = max(longest_name, len(role.name))
        return Pages.paginate("\n".join(f"{role_list[r].name} {' ' * (longest_name - len(role_list[r].name))} - {role_list[r].id}" for r in sorted(role_list.keys())))

    @commands.command()
    @commands.guild_only()
    async def roles(self, ctx: commands.Context):
        """Lists all roles on the server and their IDs, useful for configuring without having to ping that role"""
        await Pages.create_new("roles", ctx)

    @staticmethod
    def _can_act(action, ctx, user: discord.Member):
        if (ctx.author != user and user != ctx.bot.user and ctx.author.top_role > user.top_role) or \
                (ctx.guild.owner == ctx.author and ctx.author != user):
            if ctx.me.top_role > user.top_role:
                return True, None
            else:
                return False, Translator.translate(f'{action}_unable', ctx.guild.id, user=Utils.clean_user(user))
        else:
            return False, Translator.translate(f'{action}_not_allowed', ctx.guild.id, user=user)

    @commands.command(aliases=["👢"])
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason:Reason=""):
        """kick_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("kick", ctx, user)

        if allowed:
           await self.kick(ctx, user, reason, True)
        else:
            await GearbotLogging.send_to(ctx, "NO", message, translate=False)

    async def _kick(self, ctx, user, reason, confirm):
        self.bot.data["forced_exits"].add(user.id)
        await ctx.guild.kick(user,
                             reason=f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}")
        translated = Translator.translate('kick_log', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id,
                                          moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id,
                                          reason=reason)
        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS", f":boot: {translated}")
        InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, Translator.translate('kick', ctx.guild.id),
                                       reason)
        if confirm:
            await GearbotLogging.send_to(ctx, "YES", "kick_confirmation", ctx.guild.id, user=Utils.clean_user(user),
                                        user_id=user.id, reason=reason)

    @commands.guild_only()
    @commands.command("mkick")
    @commands.bot_has_permissions(kick_members=True)
    async def mkick(self, ctx, targets: Greedy[PotentialID], *, reason:Reason=""):
        """mkick help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        async def yes():
            pmessage = await GearbotLogging.send_to(ctx, "REFRESH", "processing")
            valid = 0
            failures = []
            for t in targets:
                try:
                    member = await MemberConverter().convert(ctx, str(t))
                except BadArgument as bad:
                    failures.append(f"{t}: {bad}")
                else:
                    allowed, message = self._can_act("kick", ctx, member)
                    if allowed:
                        await self._kick(ctx, member, reason, False)
                        valid+=1
                    else:
                        failures.append(f"{t}: {message}")
            await pmessage.delete()
            await GearbotLogging.send_to(ctx, "YES", "mkick_confirmation", count=valid)
            if len(failures) > 0:
                await Pages.create_new("mass_failures", ctx, action="kick", failures=Pages.paginate("\n".join(failures)))

        await Confirmation.confirm(ctx, Translator.translate("mkick_confirm", ctx), on_yes=yes)

    @staticmethod
    async def _mass_failures_init(ctx, action, failures):
        return f"**{Translator.translate(f'mass_failures_{action}', ctx, page_num=1, pages=len(failures))}**```\n{failures[0]}```", None, len(failures) > 1, []

    @staticmethod
    async def _mass_failures_update(ctx, message, page_num, action, data):
        page, page_num = Pages.basic_pages(data["failures"], page_num, action)
        action_type = data["action"]
        return f"**{Translator.translate(f'mass_failures_{action}', ctx, page_num=page_num + 1, pages=len(data['failures']))}**```\n{page}```", None, page_num

    @commands.command(aliases=["🚪"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, *, reason:Reason=""):
        """ban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("ban", ctx, user)
        if allowed:
            await self._ban(ctx, user, reason, True)
        else:
            await GearbotLogging.send_to(ctx, "NO", message, translate=False)

    async def _ban(self, ctx, user, reason, confirm):
        self.bot.data["forced_exits"].add(user.id)
        await ctx.guild.ban(user, reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}",
                            delete_message_days=0)
        InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Ban", reason)
        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                              f":door: {Translator.translate('ban_log', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason)}")
        if confirm:
            await GearbotLogging.send_to(ctx, "YES", "ban_confirmation", user=Utils.clean_user(user), user_id=user.id,
                                        reason=reason)

    @commands.guild_only()
    @commands.command()
    @commands.bot_has_permissions(ban_members=True)
    async def mban(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """mban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        async def yes():
            pmessage = await GearbotLogging.send_to(ctx, "REFRESH", "processing")
            valid = 0
            failures = []
            for t in targets:
                try:
                    member = await MemberConverter().convert(ctx, str(t))
                except BadArgument:
                    try:
                        user = await DiscordUser().convert(ctx, str(t))
                    except BadArgument as bad:
                        failures.append(f"{t}: {bad}")
                    else:
                        await self._ban(ctx, user, reason, False)
                        valid += 1
                else:
                    allowed, message = self._can_act("ban", ctx, member)
                    if allowed:
                        await self._ban(ctx, member, reason, False)
                        valid += 1
                    else:
                        failures.append(f"{t}: {message}")
            await pmessage.delete()
            await GearbotLogging.send_to(ctx, "YES", "mban_confirmation", count=valid)
            if len(failures) > 0:
                await Pages.create_new("mass_failures", ctx, action="ban",
                                       failures=Pages.paginate("\n".join(failures)))

        await Confirmation.confirm(ctx, Translator.translate("mban_confirm", ctx), on_yes=yes)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def softban(self, ctx:commands.Context, user: discord.Member, *, reason:Reason=""):
        """softban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("softban", ctx, user)
        if allowed:
            self.bot.data["forced_exits"].add(user.id)
            self.bot.data["unbans"].add(user.id)
            await ctx.guild.ban(user, reason=f"softban - Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}", delete_message_days=1)
            await ctx.guild.unban(user)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('softban_confirmation', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id, reason=reason)}")
            GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS", f":door: {Translator.translate('softban_log', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason)}")
            InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Softban", reason)

        else:
            await GearbotLogging.send_to(ctx, "NO", message, translate=False)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def forceban(self, ctx: commands.Context, user_id: UserID, *, reason:Reason=""):
        """forceban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        try:
            member = await commands.MemberConverter().convert(ctx, str(user_id))
        except BadArgument:
            user = await ctx.bot.get_user_info(user_id)
            self.bot.data["forced_exits"].add(user.id)
            await ctx.guild.ban(user, reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}",
                                delete_message_days=0)
            await ctx.send(
                f"{Emoji.get_chat_emoji('YES')} {Translator.translate('forceban_confirmation', ctx.guild.id, user=Utils.clean_user(user), user_id=user_id, reason=reason)}")
            GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                        f":door: {Translator.translate('forceban_log', ctx.guild.id, user=Utils.clean_user(user), user_id=user_id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason)}")
            InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, Translator.translate('forced_ban', ctx.guild.id), reason)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('forceban_to_ban', ctx.guild.id, user=Utils.clean_user(member))}")
            await ctx.invoke(self.ban, member, reason=reason)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, msgs: int):
        """purge_help"""
        if msgs < 1:
            return await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('purge_too_small', ctx.guild.id)}")
        if msgs > 1000:
            return await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('purge_too_big', ctx.guild.id)}")
        try:
            deleted = await ctx.channel.purge(limit=msgs)
        except discord.NotFound:
            # sleep for a sec just in case the other bot is still purging so we don't get removed as well
            await asyncio.sleep(1)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('purge_fail_not_found', ctx.guild.id)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('purge_confirmation', ctx.guild.id, count=len(deleted))}", delete_after=10)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, member: BannedMember, *, reason:Reason=""):
        """unban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        self.bot.data["unbans"].add(member.user.id)
        await ctx.guild.unban(member.user, reason=f"Moderator: {ctx.author.name} ({ctx.author.id}) Reason: {reason}")
        InfractionUtils.add_infraction(ctx.guild.id, member.user.id, ctx.author.id, "Unban", reason)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('unban_confirmation', ctx.guild.id, user=Utils.clean_user(member.user), user_id=member.user.id, reason=reason)}")
        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                    f"{Emoji.get_chat_emoji('INNOCENT')} {Translator.translate('unban_log', ctx.guild.id, user=Utils.clean_user(member.user), user_id=member.user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason)}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, target: discord.Member, durationNumber: int, durationIdentifier: Duration, *,
                   reason:Reason=""):
        """mute_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        roleid = Configuration.get_var(ctx.guild.id, "MUTE_ROLE")
        if roleid is 0:
            await ctx.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_not_configured', ctx.guild.id, user=target.mention)}")
        else:
            role = ctx.guild.get_role(roleid)
            if role is None:
                await ctx.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_role_missing', ctx.guild.id, user=target.mention)}")
            else:
                if (ctx.author != target and target != ctx.bot.user and ctx.author.top_role > target.top_role) or ctx.guild.owner == ctx.author:
                    duration = Utils.convertToSeconds(durationNumber, durationIdentifier)
                    if duration > 0:
                        until = time.time() + duration
                        await target.add_roles(role, reason=f"{reason}, as requested by {ctx.author.name}")
                        if not str(ctx.guild.id) in self.mutes:
                            self.mutes[str(ctx.guild.id)] = dict()
                        self.mutes[str(ctx.guild.id)][str(target.id)] = until
                        await ctx.send(f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_confirmation', ctx.guild.id, user=Utils.clean_user(target), duration=f'{durationNumber} {durationIdentifier}')}")
                        Utils.saveToDisk("mutes", self.mutes)
                        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_log', ctx.guild.id, user=Utils.clean_user(target), user_id=target.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, duration=f'{durationNumber} {durationIdentifier}', reason=reason)}")
                        InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Mute", reason)
                    else:
                        await ctx.send(f"{Emoji.get_chat_emoji('WHAT')} {Translator.translate('mute_negative_denied', ctx.guild.id, duration=f'{durationNumber} {durationIdentifier}')} {Emoji.get_chat_emoji('WHAT')}")
                else:
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_not_allowed', ctx.guild.id, user=target)}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, target: discord.Member, *, reason:Reason=""):
        """unmute_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        roleid = Configuration.get_var(ctx.guild.id, "MUTE_ROLE")
        if roleid is 0:
            await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} The mute feature has been disabled on this server, as such i cannot unmute that person")
        else:
            role = ctx.guild.get_role(roleid)
            if role is None:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} Unable to comply, the role i've been told to use for muting no longer exists")
            else:
                await target.remove_roles(role, reason=f"Unmuted by {ctx.author.name}, {reason}")
                await ctx.send(f"{Emoji.get_chat_emoji('INNOCENT')} {target.display_name} has been unmuted")
                GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                            f"{Emoji.get_chat_emoji('INNOCENT')} {target.name}#{target.discriminator} (`{target.id}`) has been unmuted by {ctx.author.name}")
                InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Unmute", reason)

    @commands.command()
    async def userinfo(self, ctx: commands.Context, *, user:DiscordUser=None):
        """Shows information about the chosen user"""
        if user is None:
            user = member = ctx.author
        else:
            member = None if ctx.guild is None else ctx.guild.get_member(user.id)
        embed = discord.Embed(color=0x7289DA, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=Translator.translate('requested_by', ctx, user=ctx.author.name), icon_url=ctx.author.avatar_url)
        embed.add_field(name=Translator.translate('name', ctx), value=f"{user.name}#{user.discriminator}", inline=True)
        embed.add_field(name=Translator.translate('id', ctx), value=user.id, inline=True)
        embed.add_field(name=Translator.translate('bot_account', ctx), value=user.bot, inline=True)
        embed.add_field(name=Translator.translate('animated_avatar', ctx), value=user.is_avatar_animated(), inline=True)
        if member is not None:
            account_joined = member.joined_at.strftime("%d-%m-%Y")
            embed.add_field(name=Translator.translate('nickname', ctx), value=member.nick, inline=True)
            embed.add_field(name=Translator.translate('top_role', ctx), value=member.top_role.name, inline=True)
            embed.add_field(name=Translator.translate('joined_at', ctx),
                            value=f"{account_joined} ({(ctx.message.created_at - member.joined_at).days} days ago)",
                            inline=True)
        account_made = user.created_at.strftime("%d-%m-%Y")
        embed.add_field(name=Translator.translate('account_created_at', ctx),
                        value=f"{account_made} ({(ctx.message.created_at - user.created_at).days} days ago)",
                        inline=True)
        embed.add_field(name=Translator.translate('avatar_url', ctx), value=f"[{Translator.translate('avatar_url', ctx)}]({user.avatar_url})")
        await ctx.send(embed=embed)

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
        embed = discord.Embed(color=0x7289DA, timestamp= datetime.datetime.fromtimestamp(time.time()))
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.set_footer(text=Translator.translate('requested_by', ctx, user=ctx.author), icon_url=ctx.author.avatar_url)
        embed.add_field(name=Translator.translate('name', ctx), value=ctx.guild.name, inline=True)
        embed.add_field(name=Translator.translate('id', ctx), value=ctx.guild.id, inline=True)
        embed.add_field(name=Translator.translate('owner', ctx), value=ctx.guild.owner, inline=True)
        embed.add_field(name=Translator.translate('members', ctx), value=ctx.guild.member_count, inline=True)
        embed.add_field(name=Translator.translate('text_channels', ctx), value=str(len(ctx.guild.text_channels)), inline=True)
        embed.add_field(name=Translator.translate('voice_channels', ctx), value=str(len(ctx.guild.voice_channels)), inline=True)
        embed.add_field(name=Translator.translate('total_channel', ctx), value=str(len(ctx.guild.text_channels) + len(ctx.guild.voice_channels)),
                        inline=True)
        embed.add_field(name=Translator.translate('created_at', ctx),
                        value=f"{guild_made} ({(ctx.message.created_at - ctx.guild.created_at).days} days ago)",
                        inline=True)
        embed.add_field(name=Translator.translate('vip_features', ctx), value=guild_features, inline=True)
        if ctx.guild.icon_url != "":
            embed.add_field(name=Translator.translate('server_icon', ctx), value=f"[{Translator.translate('server_icon', ctx)}]({ctx.guild.icon_url})", inline=True)
        embed.add_field(name=Translator.translate('all_roles', ctx), value=", ".join(role_list), inline=True) #todo paginate
        await ctx.send(embed=embed)

    @commands.group()
    @commands.bot_has_permissions(attach_files=True)
    async def archive(self, ctx):
        await ctx.trigger_typing()

    @archive.command()
    async def channel(self, ctx, channel:discord.TextChannel=None, amount=100):
        if amount > 5000:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_too_much', ctx)}")
            return
        if channel is None:
            channel = ctx.message.channel
        if Configuration.get_var(ctx.guild.id, "EDIT_LOGS"):
            permissions = channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.read_message_history:
                messages = LoggedMessage.select().where((LoggedMessage.server == ctx.guild.id) & (LoggedMessage.channel == channel.id)).order_by(LoggedMessage.messageid.desc()).limit(amount)
                await Archive.ship_messages(ctx, messages)
            else:
                ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_denied_read_perms')}")
        else:
            await ctx.send("Not implemented, please enable edit logs to be able to use archiving")


    @archive.command()
    async def user(self, ctx, user:UserID, amount=100):
        if amount > 5000:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_too_much', ctx)}")
            return
        if Configuration.get_var(ctx.guild.id, "EDIT_LOGS"):
            messages = LoggedMessage.select().where(
                (LoggedMessage.server == ctx.guild.id) & (LoggedMessage.author == user)).order_by(LoggedMessage.messageid.desc()).limit(amount)
            await Archive.ship_messages(ctx, messages)
        else:
            await ctx.send("Please enable edit logs so i can archive users")

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild: discord.Guild = channel.guild
        roleid = Configuration.get_var(guild.id, "MUTE_ROLE")
        if roleid is not 0:
            role = guild.get_role(roleid)
            if role is not None and channel.permissions_for(guild.me).manage_channels:
                if isinstance(channel, discord.TextChannel):
                    await channel.set_permissions(role, reason=Translator.translate('mute_setup', guild.id), send_messages=False,
                                                  add_reactions=False)
                else:
                    await channel.set_permissions(role, reason=Translator.translate('mute_setup', guild.id), speak=False, connect=False)

    async def on_member_join(self, member: discord.Member):
        if str(member.guild.id) in self.mutes and member.id in self.mutes[str(member.guild.id)]:
            roleid = Configuration.get_var(member.guild.id, "MUTE_ROLE")
            if roleid is not 0:
                role = member.guild.get_role(roleid)
                if role is not None:
                    if member.guild.me.guild_permissions.manage_roles:
                        await member.add_roles(role, reason=Translator.translate('mute_reapply_reason', member.guild.id))
                        GearbotLogging.log_to(member.guild.id, "MOD_ACTIONS",f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_reapply_log', member.guild.id, user=Utils.clean_user(member), user_id=member.id)}")
                    else:
                        GearbotLogging.log_to(member.guild.id, "MOD_ACTIONS", Translator.translate('mute_reapply_failed_log', member.build.id))

    async def on_guild_remove(self, guild: discord.Guild):
        if guild.id in self.mutes.keys():
            del self.mutes[guild.id]
            Utils.saveToDisk("mutes", self.mutes)


def setup(bot):
    bot.add_cog(Moderation(bot))


async def unmuteTask(modcog: Moderation):
    GearbotLogging.info("Started unmute background task")
    skips = []
    updated = False
    while modcog.running:
        userid = 0
        guildid = 0
        try:
            guildstoremove = []
            for guildid, list in modcog.mutes.items():
                guild: discord.Guild = modcog.bot.get_guild(int(guildid))
                toremove = []
                if Configuration.get_var(int(guildid), "MUTE_ROLE") is 0:
                    guildstoremove.append(guildid)
                for userid, until in list.items():
                    if time.time() > until and userid not in skips:
                        member = guild.get_member(int(userid))
                        role = guild.get_role(Configuration.get_var(int(guildid), "MUTE_ROLE"))
                        if member is not None:
                            if guild.me.guild_permissions.manage_roles:
                                await member.remove_roles(role, reason="Mute expired")
                                GearbotLogging.log_to(guild.id, "MOD_ACTIONS",
                                                            f"<:gearInnocent:465177981287923712> {member.name}#{member.discriminator} (`{member.id}`) has automaticaly been unmuted")
                            else:
                                GearbotLogging.log_to(guild.id, "MOD_ACTIONS",
                                                            f":no_entry: ERROR: {member.name}#{member.discriminator} (`{member.id}`) was muted earlier but I no longer have the permissions needed to unmute this person, please remove the role manually!")
                        updated = True
                        toremove.append(userid)
                for todo in toremove:
                    del list[todo]
                await asyncio.sleep(0)
            if updated:
                Utils.saveToDisk("mutes", modcog.mutes)
                updated = False
            for id in guildstoremove:
                del modcog.mutes[id]
            await asyncio.sleep(10)
        except CancelledError:
            pass  # bot shutdown
        except Exception as ex:
            GearbotLogging.error("Something went wrong in the unmute task")
            GearbotLogging.error(traceback.format_exc())
            skips.append(userid)
            embed = discord.Embed(colour=discord.Colour(0xff0000),
                                  timestamp=datetime.datetime.utcfromtimestamp(time.time()))

            embed.set_author(name="Something went wrong in the unmute task:")
            embed.add_field(name="Current guildid", value=guildid)
            embed.add_field(name="Current userid", value=userid)
            embed.add_field(name="Exception", value=ex)
            v = ""
            for line in traceback.format_exc().splitlines():
                if len(v) + len(line) > 1024:
                    embed.add_field(name="Stacktrace", value=v)
                    v = ""
                v = f"{v}\n{line}"
            if len(v) > 0:
                embed.add_field(name="Stacktrace", value=v)
            await GearbotLogging.bot_log(embed=embed)
            await asyncio.sleep(10)
    GearbotLogging.info("Unmute background task terminated")
