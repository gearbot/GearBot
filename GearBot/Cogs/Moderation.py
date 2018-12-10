import asyncio
import datetime
import time

import discord
from discord import Object
from discord.ext import commands
from discord.ext.commands import BadArgument, Greedy, MemberConverter, RoleConverter

from Util import Permissioncheckers, Configuration, Utils, GearbotLogging, Pages, InfractionUtils, Emoji, Translator, \
    Archive, Confirmation, GlobalHandlers
from Util.Converters import BannedMember, UserID, Reason, Duration, DiscordUser, PotentialID, RoleMode, Guild, \
    RangedInt, Message
from database.DatabaseConnector import LoggedMessage, Infraction


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
        self.running = True
        self.handling = set()
        self.bot.loop.create_task(self.timed_actions())
        Pages.register("roles", self.roles_init, self.roles_update)
        Pages.register("mass_failures", self._mass_failures_init, self._mass_failures_update)

    def __unload(self):
        self.running = False
        Pages.unregister("roles")

    async def __local_check(self, ctx):
        return Permissioncheckers.check_permission(ctx)

    async def roles_init(self, ctx, mode):
        pages = self.gen_roles_pages(ctx.guild, mode=mode)
        page = pages[0]
        return f"**{Translator.translate('roles', ctx.guild.id, server_name=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{page}```", None, len(
            pages) > 1, []

    async def roles_update(self, ctx, message, page_num, action, data):
        pages = self.gen_roles_pages(message.guild, mode=data["mode"])
        page, page_num = Pages.basic_pages(pages, page_num, action)
        return f"**{Translator.translate('roles', message.guild.id, server_name=ctx.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```", None, page_num

    @staticmethod
    def gen_roles_pages(guild: discord.Guild, mode):
        role_list = dict()
        longest_name = 1
        for role in guild.roles:
            role_list[f"{role.name} - {role.id}"] = role
            longest_name = max(longest_name, len(role.name))
        if mode == "alphabetic":
            return Pages.paginate("\n".join(
                f"{role_list[r].name} {' ' * (longest_name - len(role_list[r].name))} - {role_list[r].id}" for r in
                sorted(role_list.keys())))
        else:
            return Pages.paginate("\n".join(
                f"{role_list[r].name} {' ' * (longest_name - len(role_list[r].name))} - {role_list[r].id}" for r in
                reversed(list(role_list.keys()))))

    @commands.command()
    @commands.guild_only()
    async def roles(self, ctx: commands.Context, mode: RoleMode = "hierarchy"):
        """roles_help"""
        await Pages.create_new("roles", ctx, mode=mode)

    @staticmethod
    def _can_act(action, ctx, user: discord.Member):
        if ((ctx.author != user and user != ctx.bot.user and ctx.author.top_role > user.top_role) or (
                ctx.guild.owner == ctx.author and ctx.author != user)) and user != ctx.guild.owner:
            if ctx.me.top_role > user.top_role:
                return True, None
            else:
                return False, Translator.translate(f'{action}_unable', ctx.guild.id, user=Utils.clean_user(user))
        else:
            return False, Translator.translate(f'{action}_not_allowed', ctx.guild.id, user=user)
@commands.command()
    @commands.guild_only()
    async def seen(self, ctx, user: discord.Member):
        messages = LoggedMessage.select().where((LoggedMessage.server==ctx.guild.id) & (LoggedMessage.author==user.id)).order_by(LoggedMessage.messageid.desc()).limit(1)
        if len(messages) is 0:
            await GearbotLogging.send_to(ctx, "SPY", "seen_fail", user_id=user.id, user=Utils.clean_user(user))
        else:
            await GearbotLogging.send_to(ctx, "EYES", "seen_success", user_id=user.id, user=Utils.clean_user(user), date=Object(messages[0].messageid).created_at)


    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self, ctx: commands.Context):
        """mod_role_help"""
        if ctx.subcommand_passed is None:
            await ctx.invoke(self.bot.get_command("help"), "role")

    async def role_handler(self, ctx, user, role, action):
        try:
            drole = RoleConverter().convert(ctx, role)
        except BadArgument:
            # todo: try finding partial matches
            drole = None

        if role is None:
            await GearbotLogging.send_to(ctx, 'NO', 'role_not_found', role=role)
        elif self._can_act("role_add", ctx, user, ):
            await getattr(user, f"{action}_roles")(drole)
            await ctx.send(
                f"{Emoji.get_chat_emoji('YES')} {Translator.translate('mrole_added', ctx, user=await Utils.clean(user), user_id=user.id, role=role.name)}")

    @role.command()
    async def add(self, ctx, user: discord.Member, *, role: str):
        """role_add_help"""
        await self.role_handler(ctx, user, role, "add")

    # @mrole.command()
    # async def remove(self, ctx, user: discord.Member, *, rolename:str):
    #     """Removes an role to someone."""
    #     role = discord.utils.find(lambda m: rolename.lower() in m.name.lower(), ctx.guild.roles)
    #     if not role:
    #         return await ctx.send(f"{Translator.translate('role_not_found', ctx)}")
    #     elif role > ctx.guild.me.top_role:
    #         return await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mrole_remove_too_high', ctx, user=Utils.clean(user), role=role.name)}")
    #     elif user.top_role > ctx.author.top_role:
    #         return await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('user_mrole_remove_too_high', ctx, user=await Utils.clean(user), user_id=user.id, role=role.name)}")
    #     elif role == ctx.author.top_role:
    #         return await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('author_mrole_remove_same', ctx, user=await Utils.clean(user), user_id=user.id, role=role.name)}")
    #     try:
    #         await user.remove_roles(role)
    #         await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('mrole_removed', ctx, user=await Utils.clean(user), user_id=user.id, role=role.name)}")
    #     except discord.Forbidden:
    #         await ctx.send("I need **Manage Roles** for this!")

    @commands.command(aliases=["👢"])
    @commands.guild_only()
    @commands.bot_has_permissions(kick_members=True)
    async def kick(self, ctx, user: discord.Member, *, reason: Reason = ""):
        """kick_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("kick", ctx, user)

        if allowed:
            await self._kick(ctx, user, reason, True)
        else:
            await GearbotLogging.send_to(ctx, "NO", message, translate=False)

    async def _kick(self, ctx, user, reason, confirm):
        self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
        await ctx.guild.kick(user,
                             reason=Utils.trim_message(
                                 f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}",
                                 500))
        translated = Translator.translate('kick_log', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id,
                                          moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id,
                                          reason=reason)
        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS", f":boot: {translated}")
        InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, Translator.translate('kick', ctx.guild.id),
                                       reason, active=False)
        if confirm:
            await GearbotLogging.send_to(ctx, "YES", "kick_confirmation", ctx.guild.id, user=Utils.clean_user(user),
                                         user_id=user.id, reason=reason)

    @commands.guild_only()
    @commands.command("mkick")
    @commands.bot_has_permissions(kick_members=True)
    async def mkick(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
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
                        valid += 1
                    else:
                        failures.append(f"{t}: {message}")
            await pmessage.delete()
            await GearbotLogging.send_to(ctx, "YES", "mkick_confirmation", count=valid)
            if len(failures) > 0:
                await Pages.create_new("mass_failures", ctx, action="kick",
                                       failures=Pages.paginate("\n".join(failures)))

        await Confirmation.confirm(ctx, Translator.translate("mkick_confirm", ctx), on_yes=yes)

    @staticmethod
    async def _mass_failures_init(ctx, action, failures):
        return f"**{Translator.translate(f'mass_failures_{action}', ctx, page_num=1, pages=len(failures))}**```\n{failures[0]}```", None, len(
            failures) > 1, []

    @staticmethod
    async def _mass_failures_update(ctx, message, page_num, action, data):
        page, page_num = Pages.basic_pages(data["failures"], page_num, action)
        action_type = data["action"]
        return f"**{Translator.translate(f'mass_failures_{action}', ctx, page_num=page_num + 1, pages=len(data['failures']))}**```\n{page}```", None, page_num

    @commands.command(aliases=["🚪"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, user: discord.Member, *, reason: Reason = ""):
        """ban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("ban", ctx, user)
        if allowed:
            await self._ban(ctx, user, reason, True)
        else:
            await GearbotLogging.send_to(ctx, "NO", message, translate=False)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def tempban(self, ctx: commands.Context, user: discord.Member, durationNumber: int,
                      durationIdentifier: Duration, *, reason: Reason = ""):
        """ban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("ban", ctx, user)
        if allowed:
            duration = Utils.convertToSeconds(durationNumber, durationIdentifier)
            if duration > 0:
                until = time.time() + duration
                self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
                await ctx.guild.ban(user, reason=Utils.trim_message(
                    f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                                    delete_message_days=0)
                InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Tempban", reason, end=until)
                translated = Translator.translate('tempban_log', ctx.guild.id, user=Utils.clean_user(user),
                                                  user_id=user.id,
                                                  moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id,
                                                  reason=reason,
                                                  until=datetime.datetime.utcfromtimestamp(until))
                GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS", f":door: {translated}")
                await GearbotLogging.send_to(ctx, "YES", "tempban_confirmation", user=Utils.clean_user(user),
                                             user_id=user.id, reason=reason,
                                             until=datetime.datetime.utcfromtimestamp(until))
        else:
            await GearbotLogging.send_to(ctx, "NO", message, translate=False)

    async def _ban(self, ctx, user, reason, confirm):
        self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
        await ctx.guild.ban(user, reason=Utils.trim_message(
            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                            delete_message_days=0)
        Infraction.update(active=False).where((Infraction.user_id == user.id) & (Infraction.type == "Unban") & (
                    Infraction.guild_id == ctx.guild.id)).execute()
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
    async def softban(self, ctx: commands.Context, user: discord.Member, *, reason: Reason = ""):
        """softban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("softban", ctx, user)
        if allowed:
            self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
            self.bot.data["unbans"].add(user.id)
            await ctx.guild.ban(user, reason=Utils.trim_message(
                f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                                delete_message_days=1)
            await ctx.guild.unban(user)
            await ctx.send(
                f"{Emoji.get_chat_emoji('YES')} {Translator.translate('softban_confirmation', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id, reason=reason)}")
            GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                  f":door: {Translator.translate('softban_log', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason)}")
            InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Softban", reason, active=False)

        else:
            await GearbotLogging.send_to(ctx, "NO", message, translate=False)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def forceban(self, ctx: commands.Context, user_id: UserID, *, reason: Reason = ""):
        """forceban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        try:
            member = await commands.MemberConverter().convert(ctx, str(user_id))
        except BadArgument:
            user = await ctx.bot.get_user_info(user_id)
            self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
            await ctx.guild.ban(user, reason=Utils.trim_message(
                f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                                delete_message_days=0)
            await ctx.send(
                f"{Emoji.get_chat_emoji('YES')} {Translator.translate('forceban_confirmation', ctx.guild.id, user=Utils.clean_user(user), user_id=user_id, reason=reason)}")
            GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                  f":door: {Translator.translate('forceban_log', ctx.guild.id, user=Utils.clean_user(user), user_id=user_id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason)}")


            tempbans = list(Infraction.select().where((Infraction.user_id == user.id) & (Infraction.type == "Tempban") &
                                          (Infraction.guild_id == ctx.guild.id)))
            if len(tempbans) > 0:
                inf = tempbans[0]
                timeframe = datetime.datetime.utcfromtimestamp(inf.end.timestamp()) - datetime.datetime.utcfromtimestamp(time.time())
                hours, remainder = divmod(int(timeframe.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                tt = Translator.translate("hours", ctx, hours=hours, minutes=minutes)
                await GearbotLogging.send_to(ctx, "WARNING", "forceban_override_tempban", user=Utils.clean_user(user), timeframe=tt, inf_id=inf.id)

            Infraction.update(active=False).where((Infraction.user_id == user.id) & ((Infraction.type == "Unban") | (Infraction.type == "Tempban")) &
                                                  (Infraction.guild_id == ctx.guild.id)).execute()
            InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Forced ban", reason)
        else:
            await ctx.send(
                f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('forceban_to_ban', ctx.guild.id, user=Utils.clean_user(member))}")
            await ctx.invoke(self.ban, member, reason=reason)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, count:RangedInt(1, 5000)):
        """purge_help"""
        await ctx.invoke(self.clean_all, count)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def unban(self, ctx, member: BannedMember, *, reason: Reason = ""):
        """unban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        fid = f"{ctx.guild.id}-{member.user.id}"
        self.bot.data["unbans"].add(fid)
        try:
            await ctx.guild.unban(member.user, reason=Utils.trim_message(
                f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500))
        except Exception as e:
            self.bot.data["unbans"].remove(fid)
            raise e
        Infraction.update(active=False).where((Infraction.user_id == member.user.id) & ((Infraction.type == "Ban") | (Infraction.type == "Tempban")) &
                                              (Infraction.guild_id == ctx.guild.id)).execute()
        InfractionUtils.add_infraction(ctx.guild.id, member.user.id, ctx.author.id, "Unban", reason)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('unban_confirmation', ctx.guild.id, user=Utils.clean_user(member.user), user_id=member.user.id, reason=reason)}")
        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                              f"{Emoji.get_chat_emoji('INNOCENT')} {Translator.translate('unban_log', ctx.guild.id, user=Utils.clean_user(member.user), user_id=member.user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason)}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, target: discord.Member, durationNumber: int,
                   durationIdentifier: Duration, *,
                   reason: Reason = ""):
        """mute_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        roleid = Configuration.get_var(ctx.guild.id, "MUTE_ROLE")
        if roleid is 0:
            await ctx.send(
                f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_not_configured', ctx.guild.id, user=target.mention)}")
        else:
            role = ctx.guild.get_role(roleid)
            if role is None:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_role_missing', ctx.guild.id, user=target.mention)}")
            else:
                if (
                        ctx.author != target and target != ctx.bot.user and ctx.author.top_role > target.top_role) or ctx.guild.owner == ctx.author:
                    duration = Utils.convertToSeconds(durationNumber, durationIdentifier)
                    if duration > 0:
                        until = time.time() + duration
                        await target.add_roles(role, reason=Utils.trim_message(
                            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}",
                            500))
                        InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Mute", reason,
                                                       end=until)
                        await ctx.send(
                            f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_confirmation', ctx.guild.id, user=Utils.clean_user(target), duration=f'{durationNumber} {durationIdentifier}')}")
                        GearbotLogging.log_to(ctx.guild.id, "MOD_ACTIONS",
                                              f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_log', ctx.guild.id, user=Utils.clean_user(target), user_id=target.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, duration=f'{durationNumber} {durationIdentifier}', reason=reason)}")
                    else:
                        await ctx.send(
                            f"{Emoji.get_chat_emoji('WHAT')} {Translator.translate('mute_negative_denied', ctx.guild.id, duration=f'{durationNumber} {durationIdentifier}')} {Emoji.get_chat_emoji('WHAT')}")
                else:
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_not_allowed', ctx.guild.id, user=target)}")

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, target: discord.Member, *, reason: Reason = ""):
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
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx: commands.Context, *, user: DiscordUser = None):
        """Shows information about the chosen user"""
        if user is None:
            user = member = ctx.author
        else:
            member = None if ctx.guild is None else ctx.guild.get_member(user.id)
        embed = discord.Embed(color=0x7289DA, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=Translator.translate('requested_by', ctx, user=ctx.author.name),
                         icon_url=ctx.author.avatar_url)
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
        embed.add_field(name=Translator.translate('avatar_url', ctx),
                        value=f"[{Translator.translate('avatar_url', ctx)}]({user.avatar_url})")
        await ctx.send(embed=embed)

    @commands.command()
    async def serverinfo(self, ctx, guild: Guild = None):
        """Shows information about the current server."""
        if guild is None:
            guild = ctx.guild
        embed = Utils.server_info(guild)
        embed.set_footer(text=Translator.translate('requested_by', ctx, user=ctx.author),
                         icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.group()
    @commands.bot_has_permissions(attach_files=True)
    async def archive(self, ctx):
        """archive_help"""
        if ctx.subcommand_passed is None:
            await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_no_subcommand', ctx, prefix=ctx.prefix)}")
        else:
            await ctx.trigger_typing()

    @archive.command()
    async def channel(self, ctx, channel: discord.TextChannel = None, amount=100):
        """archive_channel_help"""
        if amount > 5000:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_too_much', ctx)}")
            return
        if channel is None:
            channel = ctx.message.channel
        if Configuration.get_var(ctx.guild.id, "EDIT_LOGS"):
            permissions = channel.permissions_for(ctx.author)
            if permissions.read_messages and permissions.read_message_history:
                messages = LoggedMessage.select().where(
                    (LoggedMessage.server == ctx.guild.id) & (LoggedMessage.channel == channel.id)).order_by(
                    LoggedMessage.messageid.desc()).limit(amount)
                await Archive.ship_messages(ctx, messages)
            else:
                ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_denied_read_perms', ctx, prefix=ctx.prefix)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_no_edit_logs', ctx)}")

    @archive.command()
    async def user(self, ctx, user: UserID, amount=100):
        """archive_user_help"""
        if amount > 5000:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_too_much', ctx)}")
            return
        if Configuration.get_var(ctx.guild.id, "EDIT_LOGS"):
            messages = LoggedMessage.select().where(
                (LoggedMessage.server == ctx.guild.id) & (LoggedMessage.author == user)).order_by(
                LoggedMessage.messageid.desc()).limit(amount)
            await Archive.ship_messages(ctx, messages)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_no_edit_logs', ctx)}")

    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean(self, ctx):
        """clean_help"""
        if ctx.invoked_subcommand == self.clean:
            await ctx.invoke(self.bot.get_command("help"), query="clean")

    @clean.command("user")
    async def clean_user(self, ctx, users: Greedy[DiscordUser], amount: RangedInt(1) = 50):
        """clean_user_help"""
        await self._clean(ctx, amount, lambda m: any(m.author.id == user.id for user in users))

    @clean.command("bots")
    async def clean_bots(self, ctx, amount: RangedInt(1) = 50):
        """clean_bots_help"""
        await self._clean(ctx, amount, lambda m: m.author.bot)

    @clean.command("all")
    async def clean_all(self, ctx, amount: RangedInt(1, 5000)):
        """clean_all_help"""
        await self._clean(ctx, amount, lambda m: True)

    @clean.command("last")
    async def clean_last(self, ctx, durationNumber: int, durationIdentifier: Duration):
        """clean_last_help"""
        duration = Utils.convertToSeconds(durationNumber, durationIdentifier)
        until = datetime.datetime.utcfromtimestamp(time.time() - duration)
        await self._clean(ctx, 2000, lambda m: m.created_at > until)

    @clean.command("until")
    async def clean_until(self, ctx, message:Message(local_only=True)):
        """clean_until_help"""
        await self._clean(ctx, 2000, lambda m: m.id > message.id)

    @clean.command("between")
    async def clean_between(self, ctx, start: Message(local_only=True), end: Message(local_only=True)):
        """clean_between_help"""
        a = min(start.id, end.id)
        b = max(start.id, end.id)
        await self._clean(ctx, 2000, lambda m: a <= m.id <= b)


    @staticmethod
    async def _clean(ctx, amount, checker):
        counter = 0

        def check(message):
            nonlocal counter
            match = checker(message) and counter < amount
            if match:
                counter += 1
            return match

        try:
            deleted = await ctx.channel.purge(limit=min(amount * 5, 5000), check=check, before=ctx.message)
        except discord.NotFound:
            # sleep for a sec just in case the other bot is still purging so we don't get removed as well
            await asyncio.sleep(1)
            try:
                await GearbotLogging.send_to(ctx, 'YES', 'purge_fail_not_found')
            except discord.NotFound:
                pass  # sometimes people remove channels mid purge
        else:
            await GearbotLogging.send_to(ctx, "YES", "purge_confirmation", count=len(deleted))

    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild: discord.Guild = channel.guild
        roleid = Configuration.get_var(guild.id, "MUTE_ROLE")
        if roleid is not 0:
            role = guild.get_role(roleid)
            if role is not None and channel.permissions_for(guild.me).manage_channels:
                if isinstance(channel, discord.TextChannel):
                    try:
                        await channel.set_permissions(role, reason=Translator.translate('mute_setup', guild.id),
                                                      send_messages=False,
                                                      add_reactions=False)
                    except discord.Forbidden:
                        pass
                else:
                    try:
                        await channel.set_permissions(role, reason=Translator.translate('mute_setup', guild.id),
                                                      speak=False, connect=False)
                    except discord.Forbidden:
                        pass

    async def on_member_join(self, member: discord.Member):
        now = datetime.datetime.fromtimestamp(time.time())
        if Infraction.get_or_none(Infraction.type == "Mute", Infraction.active == True,
                                                            Infraction.end >= now,
                                  Infraction.guild_id == member.guild.id,
                                  Infraction.user_id == member.id):
            roleid = Configuration.get_var(member.guild.id, "MUTE_ROLE")
            if roleid is not 0:
                role = member.guild.get_role(roleid)
                if role is not None:
                    if member.guild.me.guild_permissions.manage_roles:
                        await member.add_roles(role,
                                               reason=Translator.translate('mute_reapply_reason', member.guild.id))
                        GearbotLogging.log_to(member.guild.id, "MOD_ACTIONS",
                                              f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_reapply_log', member.guild.id, user=Utils.clean_user(member), user_id=member.id)}")
                    else:
                        GearbotLogging.log_to(member.guild.id, "MOD_ACTIONS",
                                              Translator.translate('mute_reapply_failed_log', member.build.id))

    async def timed_actions(self):
        GearbotLogging.info("Started timed moderation action background task")
        while self.running:
            # actions to handle and the function handling it
            types = {
                "Mute": self._lift_mute,
                "Tempban": self._lift_tempban
            }
            now = datetime.datetime.fromtimestamp(time.time())
            limit = datetime.datetime.fromtimestamp(time.time() + 30)
            for name, action in types.items():

                for infraction in Infraction.select().where(Infraction.type == name, Infraction.active == True,
                                                            Infraction.end <= limit):
                    if infraction.id not in self.handling:
                        self.handling.add(infraction.id)
                        self.bot.loop.create_task(
                            self.run_after((infraction.end - now).total_seconds(), action(infraction)))
            await asyncio.sleep(10)
        GearbotLogging.info("Timed moderation actions background task terminated")

    async def run_after(self, delay, action):
        if delay > 0:
            await asyncio.sleep(delay)
        if self.running:  # cog got terminated, new cog is now in charge of making sure this gets handled
            await action

    async def _lift_mute(self, infraction: Infraction):
        # check if we're even still in the guild
        guild = self.bot.get_guild(infraction.guild_id)
        if guild is None:
            GearbotLogging.info(
                f"Got an expired mute for {infraction.guild_id} but i'm no longer in that server, marking mute as ended")
            return self.end_infraction(infraction)

        role = Configuration.get_var(guild.id, "MUTE_ROLE")
        member = guild.get_member(infraction.user_id)
        role = guild.get_role(role)
        if role is None or member is None:
            return self.end_infraction(infraction)  # role got removed or member left

        info = {
            "user": Utils.clean_user(member),
            "user_id": infraction.user_id,
            "inf_id": infraction.id
        }

        if role not in member.roles:
            translated = Translator.translate('mute_role_already_removed', guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
            return self.end_infraction(infraction)

        if not guild.me.guild_permissions.manage_roles:
            translated = Translator.translate('unmute_missing_perms', guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
            return self.end_infraction(infraction)

        try:
            await member.remove_roles(role, reason="Mute expired")
        except discord.Forbidden:
            translated = Translator.translate('unmute_missing_perms', guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
        except Exception as ex:
            translated = Translator.translate("unmute_unknown_error", guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
            await GlobalHandlers.handle_exception("Automatic unmuting", self.bot, ex, infraction=infraction)
        else:
            translated = Translator.translate('unmuted', guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('INNOCENT')} {translated}")
        finally:
            self.end_infraction(infraction)

    async def _lift_tempban(self, infraction):
        guild = self.bot.get_guild(infraction.guild_id)
        if guild is None:
            GearbotLogging.info(
                f"Got an expired tempban for server {infraction.guild_id} but am no longer on that server")
            return self.end_infraction(infraction)

        user = await Utils.get_user(infraction.user_id)
        info = {
            "user": Utils.clean_user(user),
            "user_id": infraction.user_id,
            "inf_id": infraction.id
        }

        if not guild.me.guild_permissions.ban_members:
            translated = Translator.translate("tempban_expired_missing_perms", guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
            return self.end_infraction(infraction)

        try:
            await guild.get_ban(user)
        except discord.NotFound:
            translated = Translator.translate("tempban_already_lifted", guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
            return self.end_infraction(infraction)

        fid = f"{guild.id}-{infraction.user_id}"
        self.bot.data["unbans"].add(fid)
        try:
            await guild.unban(user)
        except discord.Forbidden:
            self.bot.data["unbans"].remove(fid)
            translated = Translator.translate("tempban_expired_missing_perms", guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
        except Exception as ex:
            self.bot.data["unbans"].remove(fid)
            translated = Translator.translate("tempban_expired_missing_perms", guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
            await GlobalHandlers.handle_exception("Lift tempban", self.bot, ex, **info)
        else:
            translated = Translator.translate("tempban_lifted", guild.id, **info)
            GearbotLogging.log_to(guild.id, "MOD_ACTIONS", f"{Emoji.get_chat_emoji('WARNING')} {translated}")
        finally:
            self.end_infraction(infraction)

    def end_infraction(self, infraction):
        infraction.active = False
        infraction.save()
        self.handling.remove(infraction.id)


def setup(bot):
    bot.add_cog(Moderation(bot))
