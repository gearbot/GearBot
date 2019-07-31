import asyncio
import datetime
import time
import typing
from typing import Optional

import discord
from discord import Object, Emoji, Forbidden, NotFound, ActivityType
from discord.ext import commands
from discord.ext.commands import BadArgument, Greedy, MemberConverter, RoleConverter

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Configuration, Utils, GearbotLogging, Pages, InfractionUtils, Emoji, Translator, \
    Archive, Confirmation, MessageUtils, Questions, server_info
from Util.Converters import BannedMember, UserID, Reason, Duration, DiscordUser, PotentialID, RoleMode, Guild, \
    RangedInt, Message, RangedIntBan, VerificationLevel, Nickname
from database.DatabaseConnector import LoggedMessage, Infraction


class Moderation(BaseCog):

    def __init__(self, bot):
        super().__init__(bot, {
            "min": 2,
            "max": 6,
            "required": 2,
            "commands": {
                "userinfo": {"required": 2, "min": 0, "max": 6},
                "serverinfo": {"required": 2, "min": 0, "max": 6},
                "roles": {"required": 2, "min": 0, "max": 6},
                "verification": {"required": 3, "min": 2, "max": 6},
            }
        })
        self.running = True
        self.handling = set()
        self.bot.loop.create_task(self.timed_actions())
        Pages.register("roles", self.roles_init, self.roles_update)
        Pages.register("mass_failures", self._mass_failures_init, self._mass_failures_update)

    def cog_unload(self):
        self.running = False
        Pages.unregister("roles")

    async def roles_init(self, ctx, **kwargs):
        pages = self.gen_roles_pages(ctx.guild, mode=kwargs.get("mode", "hierarchy"))
        page = pages[0]
        return f"**{Translator.translate('roles', ctx.guild.id, server_name=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{page}```", None, len(pages) > 1

    async def roles_update(self, ctx, message, page_num, action, data):
        pages = self.gen_roles_pages(message.guild, mode=data.get("mode", "hierarchy"))
        page, page_num = Pages.basic_pages(pages, page_num, action)
        data["page"] = page_num
        return f"**{Translator.translate('roles', message.guild.id, server_name=message.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```", None, data

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
        data = {"mode": mode} if mode != "hierarchy" else {}
        await Pages.create_new(self.bot, "roles", ctx, **data)

    @staticmethod
    def _can_act(action, ctx, user, check_bot=True):
        if not isinstance(user, discord.Member):
            return True, None

        # Check if they aren't here anymore so we don't error if they leave first
        if user and user.top_role > ctx.guild.me.top_role:
            return False, Translator.translate(f'{action}_unable', ctx.guild.id, user=Utils.clean_user(user))

        if ((ctx.author != user and user != ctx.bot.user and ctx.author.top_role > user.top_role) or (
                ctx.guild.owner == ctx.author and ctx.author != user)) and user != ctx.guild.owner:
            return True, None
        else:
            return False, Translator.translate(f'{action}_not_allowed', ctx.guild.id, user=user)

    @commands.command()
    @commands.guild_only()
    async def seen(self, ctx, user: discord.Member):
        """seen_help"""
        messages = LoggedMessage.select().where(LoggedMessage.author == user.id).order_by(LoggedMessage.messageid.desc()).limit(1)
        if len(messages) is 0:
            await MessageUtils.send_to(ctx, "SPY", "seen_fail", user_id=user.id, user=Utils.clean_user(user))
        else:
            await MessageUtils.send_to(ctx, "EYES", "seen_success", user_id=user.id, user=Utils.clean_user(user), date=Object(messages[0].messageid).created_at)
    
    @commands.group(aliases=["nick"])
    @commands.guild_only()
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname(self, ctx: commands.Context):
        """mod_nickname_help"""
        if ctx.subcommand_passed is None:
            await ctx.invoke(self.bot.get_command("help"), query="nickname")
    
    @nickname.command("add", aliases=["set", "update", "edit"])
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname_add(self, ctx, user: discord.Member, *, nick:Nickname):
        """mod_nickname_add_help"""
        try:
            allowed, message = self._can_act("nickname", ctx, user)
            if allowed:
                self.bot.data['nickname_changes'].add(f'{user.guild.id}-{user.id}')
                if user.nick is None:
                    type = "added"
                else:
                    type = "changed"
                await user.edit(nick=nick)
                await MessageUtils.send_to(ctx, "YES", "mod_nickname_update", user=Utils.clean_user(user), nick=nick)

                name = Utils.clean_user(user)
                before_clean = "" if user.nick is None else Utils.clean_name(user.nick)
                after_clean = Utils.clean_name(nick)
                mod_name = Utils.clean_name(ctx.author)
                GearbotLogging.log_key(ctx.guild.id, f'mod_nickname_{type}', user=name, user_id=user.id,
                                       before=before_clean, after=after_clean, moderator=mod_name, moderator_id=ctx.author.id)

            else:
                await MessageUtils.send_to(ctx, "NO", message, translate=False)
        except discord.HTTPException as ex:
            await MessageUtils.send_to(ctx, "NO", "mod_nickname_other_error", user_id=user.id, user=Utils.clean_user(user), error=ex.text)

    @nickname.command("remove", aliases=["clear", "nuke", "reset"])
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname_remove(self, ctx, user: discord.Member):
        """mod_nickname_remove_help"""
        if user.nick is None:
            await MessageUtils.send_to(ctx, "WHAT", "mod_nickname_mia", user=Utils.clean_user(user))
            return
        allowed, message = self._can_act("nickname", ctx, user)
        if allowed:
            self.bot.data['nickname_changes'].add(f'{user.guild.id}-{user.id}')
            await user.edit(nick=None)
            await MessageUtils.send_to(ctx, "YES", "mod_nickname_nuked", user_id=user.id, user=Utils.clean_user(user))
            name = Utils.clean_user(user)
            before_clean = Utils.clean_name(user.nick)
            mod_name = Utils.clean_name(ctx.author)
            GearbotLogging.log_key(ctx.guild.id, 'mod_nickname_removed', user=name, user_id=user.id,
                                   before=before_clean, moderator=mod_name,
                                   moderator_id=ctx.author.id)
        else:
            await MessageUtils.send_to(ctx, "NO", "nickname_remove_unable", user_id=user.id, user=Utils.clean_user(user))


    @commands.group()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def role(self, ctx: commands.Context):
        """mod_role_help"""
        if ctx.subcommand_passed is None:
            await ctx.invoke(self.bot.get_command("help"), query="role")

    async def role_handler(self, ctx, user, role, action):
        try:
            drole = await RoleConverter().convert(ctx, role)
        except BadArgument:
            role_search = role.lower().replace(" ", "")
            roles = [r for r in ctx.guild.roles if role_search in r.name.lower().replace(" ", "")]
            if len(roles) is 1:
                drole = roles[0]
            elif len(roles) > 1:
                await MessageUtils.send_to(ctx, "NO", "role_too_many_matches", name=role.replace("@", "@\u200b"))
                return
            else:
                await MessageUtils.send_to(ctx, "NO", "role_no_matches", name=role.replace("@", "@\u200b"))
                return

        if self._can_act(f"role_{action}", ctx, user, check_bot=False):
            role_list = Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST")
            mode = Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_WHITELIST")
            mode_name = "whitelist" if mode else "blacklist"
            if (drole.id in role_list) is mode:
                if drole < ctx.me.top_role:
                    if drole < ctx.author.top_role or user == ctx.guild.owner:
                        await getattr(user, f"{action}_roles")(drole)
                        await MessageUtils.send_to(ctx, "YES", f"role_{action}_confirmation", user=Utils.clean_user(user), user_id=user.id, role=Utils.escape_markdown(drole.name))
                    else:
                        await MessageUtils.send_to(ctx, "NO", f"user_role_too_low_{action}", role=Utils.escape_markdown(drole.name))
                else:
                    await MessageUtils.send_to(ctx, "NO", f"role_too_high_{action}", role=Utils.escape_markdown(drole.name))
            else:
                await MessageUtils.send_to(ctx, "NO", f"role_denied_{mode_name}", role=Utils.escape_markdown(drole.name))

    @role.command()
    @commands.bot_has_permissions(manage_roles=True)
    async def add(self, ctx, user: discord.Member, *, role: str):
        """role_add_help"""
        await self.role_handler(ctx, user, role, "add")

    @role.command(aliases=["rmv"])
    @commands.bot_has_permissions(manage_roles=True)
    async def remove(self, ctx, user: discord.Member, *, role: str):
        """role_remove_help"""
        await self.role_handler(ctx, user, role, "remove")

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
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    async def _kick(self, ctx, user, reason, confirm):
        self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
        await ctx.guild.kick(user,
                             reason=Utils.trim_message(
                                 f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}",
                                 500))
        i = InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, 'Kick', reason, active=False)
        GearbotLogging.log_key(ctx.guild.id, 'kick_log', user=Utils.clean_user(user), user_id=user.id,
                               moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id,
                               reason=reason, inf=i.id)
        if confirm:
            await MessageUtils.send_to(ctx, "YES", "kick_confirmation", ctx.guild.id, user=Utils.clean_user(user),
                                         user_id=user.id, reason=reason, inf=i.id)

    @commands.guild_only()
    @commands.command("mkick", aliases=["👢👢"])
    @commands.bot_has_permissions(kick_members=True, add_reactions=True)
    async def mkick(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """mkick_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
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
            await MessageUtils.send_to(ctx, "YES", "mkick_confirmation", count=valid)
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action="kick",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))

        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("mkick_confirm", ctx), on_yes=yes)
        else:
            await self.empty_list(ctx, "kick")

    @staticmethod
    async def _mass_failures_init(ctx, action, failures):
        failures = failures.split("----NEW PAGE----")
        return f"**{Translator.translate(f'mass_failures_{action}', ctx, page_num=1, pages=len(failures))}**```\n{failures[0]}```", None, len(failures) > 1

    @staticmethod
    async def _mass_failures_update(ctx, message, page_num, action, data):
        page, page_num = Pages.basic_pages(data["failures"].split("----NEW PAGE----"), page_num, action)
        action_type = data["action"]
        data["page"] = page_num
        return f"**{Translator.translate(f'mass_failures_{action_type}', ctx, page_num=page_num + 1, pages=len(data['failures']))}**```\n{page}```", None, data

    @commands.guild_only()
    @commands.command()
    async def bean(self, ctx, user: discord.Member, *, reason: Reason = ""):
        """bean_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        allowed, message = self._can_act("bean", ctx, user)
        if allowed:
            await MessageUtils.send_to(ctx, "YES", "bean_confirmation", user=Utils.clean_user(user), user_id=user.id, reason=reason)
            try :
                message = await self.bot.wait_for("message", timeout=60*5, check=lambda m: m.author == user and m.channel.guild == ctx.guild and m.channel.permissions_for(m.guild.me).add_reactions)
            except asyncio.TimeoutError:
                pass
            else:
                try:
                    await message.add_reaction(Emoji.get_emoji('BEAN'))
                except Forbidden:
                    await message.channel.send(Emoji.get_chat_emoji('BEAN'))
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    @commands.command(aliases=["🚪"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True, add_reactions=True)
    async def ban(self, ctx: commands.Context, user: DiscordUser, *, reason: Reason = ""):
        """ban_help"""
        if ctx.guild.get_member(user.id) is not None:
            member = ctx.guild.get_member(user.id)
            await self._ban_command(ctx, member, reason, 0)
        else:
            async def yes():
                await ctx.invoke(self.forceban, user=user, reason=reason)

            await Confirmation.confirm(ctx, MessageUtils.assemble(ctx, "SINISTER", 'ban_user_not_here', user=Utils.clean_user(user)), on_yes=yes)

    @commands.command(aliases=["clean_ban"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def cleanban(self, ctx: commands.Context, user: DiscordUser, days: Optional[RangedIntBan]=1, *, reason: Reason = ""):
        """clean_ban_help"""
        await self._ban_command(ctx, user, reason, days)

    async def _ban_command(self, ctx, user, reason, days):
        member = ctx.guild.get_member(user.id)

        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("ban", ctx, member)
        if allowed:
            await self._ban(ctx, user, reason, True, days=days)
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def tempban(self, ctx: commands.Context, user: DiscordUser, duration: Duration, *, reason: Reason = ""):
        """tempban_help"""
        if duration.unit is None:
            parts = reason.split(" ")
            duration.unit = parts[0]
            reason = " ".join(parts[1:])

        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        member = ctx.guild.get_member(user.id)
        if member is not None:
            allowed, message = self._can_act("ban", ctx, member)
        else:
            allowed = True
        if allowed:
            duration_seconds = duration.to_seconds(ctx)
            if duration_seconds > 0:

                self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
                await ctx.guild.ban(user, reason=Utils.trim_message(
                    f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                                    delete_message_days=0)
                until = time.time() + duration_seconds
                i = InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Tempban", reason, end=until)
                GearbotLogging.log_key(ctx.guild.id, 'tempban_log', user=Utils.clean_user(user), user_id=user.id,
                                       moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason,
                                       until=datetime.datetime.utcfromtimestamp(until), inf=i.id)
                await MessageUtils.send_to(ctx, "YES", "tempban_confirmation", user=Utils.clean_user(user),
                                             user_id=user.id, reason=reason,
                                             until=datetime.datetime.utcfromtimestamp(until), inf=i.id)
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    async def _ban(self, ctx, user, reason, confirm, days=0):
        self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
        await ctx.guild.ban(user, reason=Utils.trim_message(
            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                            delete_message_days=days)
        Infraction.update(active=False).where((Infraction.user_id == user.id) & (Infraction.type == "Unban") & (
                    Infraction.guild_id == ctx.guild.id)).execute()
        i = InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Ban", reason)
        GearbotLogging.log_key(ctx.guild.id, 'ban_log', user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason, inf=i.id)
        if confirm:
            await MessageUtils.send_to(ctx, "YES", "ban_confirmation", user=Utils.clean_user(user), user_id=user.id,
                                         reason=reason, inf=i.id)

    async def _unban(self, ctx, user, reason, confirm, days=0):
        self.bot.data["unbans"].add(f"{ctx.guild.id}-{user.id}")
        await ctx.guild.unban(user, reason=Utils.trim_message(
            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500))
        Infraction.update(active=False).where((Infraction.user_id == user.id) & ((Infraction.type == "Ban") | (Infraction.type == "Tempban")) &
                                              (Infraction.guild_id == ctx.guild.id)).execute()
        i = InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Unban", reason)
        GearbotLogging.log_to(ctx.guild.id, 'unban_log', user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author),
                                moderator_id=ctx.author.id, reason=reason, inf=i.id)
        if confirm:
            await MessageUtils.send_to(ctx, "YES", "unban_confirmation", user=Utils.clean_user(user), user_id=user.id,
                                         reason=reason, inf=i.id)

    @commands.guild_only()
    @commands.command(aliases=["🚪🚪"])
    @commands.bot_has_permissions(ban_members=True, add_reactions=True)
    async def mban(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """mban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
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
            await MessageUtils.send_to(ctx, "YES", "mban_confirmation", count=valid)
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action="ban",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))
        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("mban_confirm", ctx), on_yes=yes)
        else:
            await self.empty_list(ctx, "ban")

    @commands.guild_only()
    @commands.command()
    @commands.bot_has_permissions(ban_members=True, add_reactions=True)
    async def munban(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """munban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
            valid = 0
            failures = []
            for t in targets:
                try:
                    user = await DiscordUser().convert(ctx, str(t))
                except BadArgument as bad:
                    failures.append(f"{t}: {bad}")
                else:
                    try:
                        await self._unban(ctx, user, reason, False)
                    except NotFound:
                        ban_not_found = Translator.translate("ban_not_found", ctx)
                        failures.append(f"{t}: {ban_not_found}")
                    else:
                        valid += 1
            await pmessage.delete()
            await MessageUtils.send_to(ctx, "YES", "munban_confirmation", count=valid)
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action="unban",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))
        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("munban_confirm", ctx), on_yes=yes)
        else:
            await self.empty_list(ctx, "unban")

    @staticmethod
    async def empty_list(ctx, action):
        message = await ctx.send(f"{Translator.translate('m_nobody', ctx, action=action)} {Emoji.get_chat_emoji('THINK')}")
        await asyncio.sleep(3)
        message2 = await ctx.send(f"{Translator.translate('m_nobody_2', ctx)} {Emoji.get_chat_emoji('WINK')}")
        await asyncio.sleep(3)
        await message.edit(content=Translator.translate('intimidation', ctx))
        await message2.delete()

    @commands.command(aliases=["softban"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def cleankick(self, ctx: commands.Context, user: discord.Member, *, reason: Reason = ""):
        """softban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)

        allowed, message = self._can_act("softban", ctx, user)
        if allowed:
            self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
            self.bot.data["unbans"].add(f"{ctx.guild.id}-{user.id}")
            i = InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Softban", reason, active=False)
            await ctx.guild.ban(user, reason=Utils.trim_message(
                f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                                delete_message_days=1)
            await ctx.guild.unban(user)
            await MessageUtils.send_to(ctx, 'YES', 'softban_confirmation', user=Utils.clean_user(user), user_id=user.id, reason=reason, inf=i.id)
            GearbotLogging.log_key(ctx.guild.id, 'softban_log', user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason, inf=i.id)
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    @commands.command()
    @commands.guild_only()
    async def slowmode(self, ctx: commands.Context, channel: typing.Optional[discord.TextChannel], duration: Duration):
        """slowmode_help"""
        if channel is None:
            channel = ctx.channel
        duration_seconds = duration.to_seconds(ctx)
        if duration_seconds > 21600:
            await MessageUtils.send_to(ctx, 'NO', "slowmode_too_high")
        elif channel.slowmode_delay == duration_seconds:
            await MessageUtils.send_to(ctx, 'NO', "slowmode_no_change", duration=duration, channel=channel.mention)
        else:
            try:
                await channel.edit(slowmode_delay=duration_seconds)
            except discord.Forbidden:
                await MessageUtils.send_to(ctx, 'NO', "slowmode_no_perms", channel=channel.mention)
            else:
                GearbotLogging.log_key(ctx.guild.id, "slowmode_log", user=Utils.escape_markdown(ctx.author), user_id=ctx.author.id, channel=channel.mention, channel_id=channel.id, duration=duration)
                await MessageUtils.send_to(ctx, 'YES', "slowmode_set", duration=duration, channel=channel.mention)
    
    @commands.command()
    @commands.guild_only()
    async def verification(self, ctx: commands.Context, level: VerificationLevel, *, reason: Reason = ""):
        """verification_help"""
        if reason == "":
            reason = Translator.translate('no_reason', ctx)
        if ctx.guild.verification_level != level:
            try:
                await ctx.guild.edit(verification_level=level, reason=reason)
            except discord.Forbidden:
                await MessageUtils.send_to(ctx, 'NO', "verification_no_perms")
            else:
                GearbotLogging.log_key(ctx.guild.id, "verification_log", user=Utils.escape_markdown(ctx.author), user_id=ctx.author.id, level=level, reason=reason)
                await MessageUtils.send_to(ctx, 'YES', "verification_set", level=level)
        else:
            await MessageUtils.send_to(ctx, 'NO', 'verification_no_change', level=level)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True, add_reactions=True)
    async def forceban(self, ctx: commands.Context, user: DiscordUser, *, reason: Reason = ""):
        """forceban_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        # check if the user is a member
        try:
            member = await commands.MemberConverter().convert(ctx, str(user.id))
        except BadArgument:
            #they are not, check for existing ban
            try:
                await ctx.guild.fetch_ban(user)
            except NotFound:
                #not banned, wack em
                await self._forceban(ctx, user, reason)
            else:
                # already banned, ask for confirmation
                message = MessageUtils.assemble(ctx, 'QUESTION', 'forceban_banned_confirmation', user=Utils.clean_user(user))
                async def yes():
                    await self._forceban(ctx, user, reason)
                await Confirmation.confirm(ctx, message, on_yes=yes)
        else:
            # they are here, reroute to regular ban
            await MessageUtils.send_to(ctx, 'WARNING', 'forceban_to_ban', user=Utils.clean_user(member))
            await ctx.invoke(self.ban, member, reason=reason)

    async def _forceban(self, ctx, user, reason):
        # not banned, wack with the hammer
        self.bot.data["forced_exits"].add(f"{ctx.guild.id}-{user.id}")
        await ctx.guild.ban(user, reason=Utils.trim_message(
            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                            delete_message_days=0)
        Infraction.update(active=False).where(
            (Infraction.user_id == user.id) & ((Infraction.type == "Unban") | (Infraction.type == "Tempban")) &
            (Infraction.guild_id == ctx.guild.id)).execute()
        i = InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Forced ban", reason)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('forceban_confirmation', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id, reason=reason, inf=i.id)}")
        GearbotLogging.log_key(ctx.guild.id, 'forceban_log', user=Utils.clean_user(user), user_id=user.id,
                               moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason,
                               inf=i.id)

        # check for pending tembans
        tempbans = list(Infraction.select().where((Infraction.user_id == user.id) & (Infraction.type == "Tempban") &
                                                  (Infraction.guild_id == ctx.guild.id) & Infraction.active))
        if len(tempbans) > 0:
            # mark as complete and inform
            inf = tempbans[0]
            timeframe = datetime.datetime.utcfromtimestamp(inf.end.timestamp()) - datetime.datetime.utcfromtimestamp(
                time.time())
            hours, remainder = divmod(int(timeframe.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            tt = Translator.translate("hours", ctx, hours=hours, minutes=minutes)
            await MessageUtils.send_to(ctx, "WARNING", "forceban_override_tempban", user=Utils.clean_user(user),
                                       timeframe=tt, inf_id=inf.id)

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
        i = InfractionUtils.add_infraction(ctx.guild.id, member.user.id, ctx.author.id, "Unban", reason)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('unban_confirmation', ctx.guild.id, user=Utils.clean_user(member.user), user_id=member.user.id, reason=reason, inf = i.id)}")
        GearbotLogging.log_key(ctx.guild.id, 'unban_log', user=Utils.clean_user(member.user), user_id=member.user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason, inf=i.id)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True, add_reactions=True)
    async def mute(self, ctx: commands.Context, target: discord.Member, duration: Duration, *, reason: Reason = ""):
        """mute_help"""
        if duration.unit is None:
            parts = reason.split(" ")
            duration.unit = parts[0]
            reason = " ".join(parts[1:])
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        roleid = Configuration.get_var(ctx.guild.id, "ROLES", "MUTE_ROLE")
        if roleid is 0:
            await ctx.send(
                f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_not_configured', ctx.guild.id, user=target.mention)}")
        else:
            role = ctx.guild.get_role(roleid)
            if role is None:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_role_missing', ctx.guild.id, user=target.mention)}")
            else:
                if (ctx.author != target and target != ctx.bot.user and ctx.author.top_role > target.top_role) or ctx.guild.owner == ctx.author:
                    if ctx.guild.me.top_role > role:
                        duration_seconds = duration.to_seconds(ctx)
                        if duration_seconds > 0:
                            infraction = Infraction.get_or_none((Infraction.user_id == target.id) & (Infraction.type == "Mute") & (Infraction.guild_id == ctx.guild.id) & Infraction.active)
                            if infraction is None:
                                await target.add_roles(role, reason=Utils.trim_message(
                                    f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}",
                                    500))
                                until = time.time() + duration_seconds
                                i = InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Mute", reason,
                                                               end=until)
                                await MessageUtils.send_to(ctx, 'MUTE', 'mute_confirmation', user=Utils.clean_user(target),
                                                           duration=f'{duration.length} {duration.unit}', reason=reason, inf=i.id)
                                GearbotLogging.log_key(ctx.guild.id, 'mute_log',
                                                       user=Utils.clean_user(target),
                                                       user_id=target.id,
                                                       moderator=Utils.clean_user(ctx.author),
                                                       moderator_id=ctx.author.id,
                                                       duration=f'{duration.length} {duration.unit}',
                                                       reason=reason, inf=i.id)
                            else:
                                d = f'{duration.length} {duration.unit}'
                                async def extend():
                                    infraction.end += datetime.timedelta(seconds=duration_seconds)
                                    infraction.save()
                                    await MessageUtils.send_to(ctx, 'YES', 'mute_duration_extended', duration=d, end=infraction.end)
                                    GearbotLogging.log_key(ctx.guild.id, 'mute_duration_extended_log', user=Utils.clean_user(target),
                                                           user_id=target.id,
                                                           moderator=Utils.clean_user(ctx.author),
                                                           moderator_id=ctx.author.id,
                                                           duration=f'{duration.length} {duration.unit}',
                                                           reason=reason, inf_id=infraction.id, end=infraction.end)

                                async def until():
                                    infraction.end = time.time() + duration_seconds
                                    infraction.save()
                                    await MessageUtils.send_to(ctx, 'YES', 'mute_duration_added', duration=d)
                                    GearbotLogging.log_key(ctx.guild.id, 'mute_duration_added_log',
                                                           user=Utils.clean_user(target),
                                                           user_id=target.id,
                                                           moderator=Utils.clean_user(ctx.author),
                                                           moderator_id=ctx.author.id,
                                                           duration=f'{duration.length} {duration.unit}',
                                                           reason=reason, inf_id=infraction.id, end=infraction.end)

                                async def overwrite():
                                    infraction.end = infraction.start + datetime.timedelta(seconds=duration_seconds)
                                    infraction.save()
                                    await MessageUtils.send_to(ctx, 'YES', 'mute_duration_overwritten', duration=d, end=infraction.end)
                                    GearbotLogging.log_key(ctx.guild.id, 'mute_duration_overwritten_log',
                                                           user=Utils.clean_user(target),
                                                           user_id=target.id,
                                                           moderator=Utils.clean_user(ctx.author),
                                                           moderator_id=ctx.author.id,
                                                           duration=f'{duration.length} {duration.unit}',
                                                           reason=reason, inf_id=infraction.id, end=infraction.end)


                                await Questions.ask(ctx, MessageUtils.assemble(ctx, 'WHAT', 'mute_options', id=infraction.id), [
                                    Questions.Option(Emoji.get_emoji("1"), Translator.translate("mute_option_extend", ctx, duration=d), extend),
                                    Questions.Option(Emoji.get_emoji("2"), Translator.translate("mute_option_until", ctx, duration=d), until),
                                    Questions.Option(Emoji.get_emoji("3"), Translator.translate("mute_option_overwrite", ctx, duration=d), overwrite)
                                ])
                        else:
                            await MessageUtils.send_to(ctx, 'NO', 'mute_negative_denied', duration=f'{duration.length} {duration.unit}')
                    else:
                        await MessageUtils.send_to(ctx, 'NO', 'role_too_high_add', role=role.name)
                else:
                    await MessageUtils.send_to(ctx, 'NO', 'mute_not_allowed', user=target)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, target: discord.Member, *, reason: Reason = ""):
        """unmute_help"""
        if reason == "":
            reason = Translator.translate("no_reason", ctx.guild.id)
        roleid = Configuration.get_var(ctx.guild.id, "ROLES", "MUTE_ROLE")
        if roleid is 0:
            await MessageUtils.send_to(ctx, 'NO', 'unmute_fail_disabled')
        else:
            role = ctx.guild.get_role(roleid)
            if role is None:
                await MessageUtils.send_to(ctx, 'NO', 'unmtue_fail_role_removed')
            else:
                infraction = Infraction.get_or_none((Infraction.user_id == target.id) & (Infraction.type == "Mute") & (Infraction.guild_id == ctx.guild.id) & Infraction.active)
                if role not in target.roles and infraction is None:
                    await MessageUtils.send_to(ctx, 'WHAT', 'unmute_not_muted', user=Utils.clean_user(target))
                else:
                    i = InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Unmute", reason)
                    Infraction.update(active=False).where((Infraction.user_id == target.id) & (Infraction.type == "Mute") & (Infraction.guild_id == ctx.guild.id)).execute()
                    await target.remove_roles(role, reason=f"Unmuted by {ctx.author.name}, {reason}")
                    await MessageUtils.send_to(ctx, 'INNOCENT', 'unmute_confirmation', user=Utils.clean_user(target), inf = i.id)
                    GearbotLogging.log_key(ctx.guild.id, 'unmute_modlog', user=Utils.clean_user(target), user_id=target.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason, inf=i.id)

    @commands.command(aliases=["info"])
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx: commands.Context, *, user: DiscordUser = None):
        """userinfo_help"""
        if user is None:
            user = member = ctx.author
        else:
            member = None if ctx.guild is None else ctx.guild.get_member(user.id)
        embed = discord.Embed(color=member.top_role.color if member is not None else 0x00cea2, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=user.avatar_url)
        embed.set_footer(text=Translator.translate('requested_by', ctx, user=ctx.author.name),
                         icon_url=ctx.author.avatar_url)
        embed.add_field(name=Translator.translate('name', ctx), value=Utils.escape_markdown(f"{user.name}#{user.discriminator}"), inline=True)
        embed.add_field(name=Translator.translate('id', ctx), value=user.id, inline=True)
        embed.add_field(name=Translator.translate('bot_account', ctx), value=user.bot, inline=True)
        if type(user.is_avatar_animated) != type(True): # When from the Redis cache, this comes back as a boolean
            embed.add_field(name=Translator.translate('animated_avatar', ctx), value=user.is_avatar_animated(), inline=True)
        else:
            embed.add_field(name=Translator.translate('animated_avatar', ctx), value=user.is_avatar_animated, inline=True)
        embed.add_field(name=Translator.translate('avatar_url', ctx),
                        value=f"[{Translator.translate('avatar_url', ctx)}]({user.avatar_url})")
        embed.add_field(name=Translator.translate("profile", ctx), value=user.mention)
        if member is not None:
            status = str(member.status)
            status_emoji = Emoji.get_chat_emoji(status.upper())
            if member.activity is not None:
                listening_emoji = Emoji.get_chat_emoji("MUSIC")
                watching_emoji = Emoji.get_chat_emoji("WATCHING")
                game_emoji = Emoji.get_chat_emoji("GAMING")
                streaming_emoji = Emoji.get_chat_emoji("STREAMING")
                if member.activity.type == ActivityType.listening:
                    embed.add_field(name=Translator.translate("activity", ctx), value=f"{listening_emoji} {Translator.translate('listening_to', ctx, song=member.activity.title)} {listening_emoji}")
                elif member.activity.type == ActivityType.watching:
                    embed.add_field(name=Translator.translate("activity", ctx), value=f"{watching_emoji} {Translator.translate('watching', ctx, name=member.activity.name)} {watching_emoji}")
                elif member.activity.type == ActivityType.streaming:
                    embed.add_field(name=Translator.translate("activity", ctx), value=f"{streaming_emoji} {Translator.translate('streaming', ctx, title=member.activity.name)} {streaming_emoji}")
                elif member.activity.type == ActivityType.playing:
                    embed.add_field(name=Translator.translate("activity", ctx), value=f"{game_emoji} {Translator.translate('playing', ctx, game=member.activity.name)} {game_emoji}")
                else:
                    embed.add_field(name=Translator.translate("activity", ctx), value=Translator.translate("unknown_activity", ctx))
            embed.add_field(name=Translator.translate("status", ctx), value=f"{status_emoji} {Translator.translate(status, ctx)} {status_emoji}")
            embed.add_field(name=Translator.translate('nickname', ctx), value=Utils.escape_markdown(member.nick), inline=True)

            role_list = [role.mention for role in reversed(member.roles) if role is not ctx.guild.default_role]
            if len(role_list) > 0:
                member_roles = Pages.paginate(" ".join(role_list))
            else:
                member_roles = [Translator.translate("no_roles", ctx)]
            embed.add_field(name=Translator.translate('all_roles', ctx), value=member_roles[0])
            if len(member_roles) > 1:
                for p in member_roles[1:]:
                    embed.add_field(name=Translator.translate("more_roles", ctx), value=p)

            embed.add_field(name=Translator.translate('joined_at', ctx),
                            value=f"{(ctx.message.created_at - member.joined_at).days} days ago (``{member.joined_at}``)",
                            inline=True)
        embed.add_field(name=Translator.translate('account_created_at', ctx),
                        value=f"{(ctx.message.created_at - user.created_at).days} days ago (``{user.created_at}``)",
                        inline=True)
        il = Infraction.select(Infraction.guild_id).where(Infraction.user_id == user.id).count()
        ild = Infraction.select(Infraction.guild_id).distinct().where(Infraction.user_id == user.id).count()
        emoji = "SINISTER" if il >= 2 else "INNOCENT"
        embed.add_field(name=Translator.translate("infractions", ctx), value=MessageUtils.assemble(ctx, emoji, "total_infractions", total=il, servers=ild))

        await ctx.send(embed=embed)

    @commands.command(aliases=["server"])
    async def serverinfo(self, ctx, guild: Guild = None):
        """serverinfo_help"""
        if guild is None:
            guild = ctx.guild
        embed = server_info.server_info_embed(guild, ctx.guild)
        embed.set_footer(text=Translator.translate('requested_by', ctx, user=ctx.author),
                         icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.group()
    @commands.bot_has_permissions(attach_files=True)
    async def archive(self, ctx):
        """archive_help"""
        if ctx.invoked_subcommand is None:
            await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_no_subcommand', ctx, prefix=ctx.prefix)}")

    @archive.command()
    async def channel(self, ctx, channel: discord.TextChannel = None, amount=100):
        """archive_channel_help"""
        if amount > 5000:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_too_much', ctx)}")
            return
        if channel is None:
            channel = ctx.message.channel
        if Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", "ENABLED"):
            await MessageUtils.send_to(ctx, 'SEARCH', 'searching_archives')
            messages = LoggedMessage.select().where(
                (LoggedMessage.server == ctx.guild.id) & (LoggedMessage.channel == channel.id)).order_by(
                LoggedMessage.messageid.desc()).limit(amount)
            await Archive.ship_messages(ctx, messages, "channel")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_no_edit_logs', ctx)}")

    @archive.command()
    async def user(self, ctx, user: UserID, amount=100):
        """archive_user_help"""
        if amount > 5000:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_too_much', ctx)}")
            return
        if Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", "ENABLED"):
            await MessageUtils.send_to(ctx, 'SEARCH', 'searching_archives')
            messages = LoggedMessage.select().where(
                (LoggedMessage.server == ctx.guild.id) & (LoggedMessage.author == user)).order_by(
                LoggedMessage.messageid.desc()).limit(amount)
            await Archive.ship_messages(ctx, messages, "user")
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
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_user(self, ctx, users: Greedy[DiscordUser], amount: RangedInt(1) = 50):
        """clean_user_help"""
        if len(users) is 0:
            await MessageUtils.send_to(ctx, 'NO', 'clean_missing_targets')
        await self._clean(ctx, amount, lambda m: any(m.author.id == user.id for user in users))

    @clean.command("bots")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_bots(self, ctx, amount: RangedInt(1) = 50):
        """clean_bots_help"""
        await self._clean(ctx, amount, lambda m: m.author.bot)

    @clean.command("all")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_all(self, ctx, amount: RangedInt(1, 5000)):
        """clean_all_help"""
        await self._clean(ctx, amount, lambda m: True, check_amount=amount)

    @clean.command("last")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_last(self, ctx, duration: Duration, excess=""):
        """clean_last_help"""
        if duration.unit is None:
            duration.unit = excess
        until = datetime.datetime.utcfromtimestamp(time.time() - duration.to_seconds(ctx))
        await self._clean(ctx, 5000, lambda m: True, after=until)

    @clean.command("until")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_until(self, ctx, message:Message(local_only=True)):
        """clean_until_help"""
        await self._clean(ctx, 5000, lambda m: True, after=Object(message.id-1))

    @clean.command("between")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_between(self, ctx, start: Message(local_only=True), end: Message(local_only=True)):
        """clean_between_help"""
        a = min(start.id, end.id)
        b = max(start.id, end.id)
        await self._clean(ctx, 5000, lambda m: True , before=Object(b+1), after=Object(a+1))

    @clean.command("everywhere")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_everywhere(self, ctx, users: Greedy[DiscordUser], amount: RangedInt(1) = 50):
        """clean_everywhere_help"""
        if len(users) is 0:
            await MessageUtils.send_to(ctx, 'NO', 'clean_missing_targets')
        total = 0
        if any(channel.id in self.bot.being_cleaned for channel in ctx.guild.text_channels):
            await MessageUtils.send_to(ctx, "NO", "already_cleaning")
            return
        self.bot.being_cleaned[ctx.channel.id] = set()
        message = await MessageUtils.send_to(ctx, "REFRESH", "processing")
        failed = set()
        for channel in ctx.guild.text_channels:
            self.bot.being_cleaned[channel.id] = set()
            try:
                counter = 0
                def check(message):
                    nonlocal counter
                    match = any(message.author.id == user.id for user in users) and counter < amount
                    if match:
                        counter += 1
                    return match
                deleted = await channel.purge(limit=250, check=check, before=ctx.message)
                total += len(deleted)
            except discord.HTTPException:
                failed.add(channel)
            finally:
                self.bot.loop.create_task(self.finish_cleaning(channel.id, ctx.guild.id))
        await MessageUtils.try_edit(message, 'YES', 'purge_everywhere_complete', count=total, channels=len(ctx.guild.text_channels) - len(failed), failed=len(failed))


    async def _clean(self, ctx, amount, checker, before=None, after=None, check_amount=None):
        counter = 0
        if ctx.channel.id in self.bot.being_cleaned:
            await MessageUtils.send_to(ctx, "NO", "already_cleaning")
            return
        self.bot.being_cleaned[ctx.channel.id] = set()
        message = await MessageUtils.send_to(ctx, "REFRESH", "processing")
        try:
            def check(message):
                nonlocal counter
                match = checker(message) and counter < amount
                if match:
                    counter += 1
                return match
            try:
                deleted = await ctx.channel.purge(limit=min(amount * 5, 5000) if check_amount is None else check_amount, check=check, before=ctx.message if before is None else before, after=after)
            except discord.NotFound:
                # sleep for a sec just in case the other bot is still purging so we don't get removed as well
                await asyncio.sleep(1)
                try:
                    await MessageUtils.try_edit(message, 'NO', 'purge_fail_not_found')
                except discord.NotFound:
                    pass  # sometimes people remove channels mid purge
            else:
                await MessageUtils.try_edit(message, "YES", "purge_confirmation", count=len(deleted))
        except Exception as ex:
            self.bot.loop.create_task(self.finish_cleaning(ctx.channel.id, ctx.guild.id))
            raise ex
        self.bot.loop.create_task(self.finish_cleaning(ctx.channel.id, ctx.guild.id))

    async def finish_cleaning(self, channel_id, guild_id):
        await asyncio.sleep(1) # make sure we received all delete events
        l = self.bot.being_cleaned[channel_id]
        del self.bot.being_cleaned[channel_id]
        await MessageUtils.archive_purge(self.bot, l, guild_id)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        guild: discord.Guild = channel.guild
        roleid = Configuration.get_var(guild.id, "ROLES", "MUTE_ROLE")
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

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        now = datetime.datetime.fromtimestamp(time.time())
        i = Infraction.get_or_none(Infraction.type == "Mute", Infraction.active == True,
                                                            Infraction.end >= now,
                                  Infraction.guild_id == member.guild.id,
                                  Infraction.user_id == member.id)
        if i is not None:
            roleid = Configuration.get_var(member.guild.id, "ROLES", "MUTE_ROLE")
            if roleid is not 0:
                role = member.guild.get_role(roleid)
                if role is not None:
                    if member.guild.me.guild_permissions.manage_roles:
                        try:
                            await member.add_roles(role,
                                               reason=Translator.translate('mute_reapply_reason', member.guild.id))
                        except NotFound:
                            pass  # probably kicked out again by antiraid, nothing to do here
                        GearbotLogging.log_key(member.guild.id, 'mute_reapply_log', user=Utils.clean_user(member), user_id=member.id, inf=i.id)
                    else:
                        GearbotLogging.log_key(member.guild.id, 'mute_reapply_failed_log', inf=i.id)

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

        role = Configuration.get_var(guild.id, "ROLES", "MUTE_ROLE")
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
            GearbotLogging.log_key(guild.id, 'mute_role_already_removed', **info)
            return self.end_infraction(infraction)

        if not guild.me.guild_permissions.manage_roles:
            GearbotLogging.log_key(guild.id, "unmute_missing_perms", **info)
            return self.end_infraction(infraction)

        try:
            await member.remove_roles(role, reason="Mute expired")
        except discord.Forbidden:
            GearbotLogging.log_key(guild.id, "unmute_missing_perms", **info)
        except Exception as ex:
            GearbotLogging.log_key(guild.id, 'unmute_unknown_error', **info)
            await TheRealGearBot.handle_exception("Automatic unmuting", self.bot, ex, infraction=infraction)
        else:
            GearbotLogging.log_key(guild.id, 'unmuted', **info)
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
            GearbotLogging.log_key(guild.id, 'tempban_expired_missing_perms', **info)
            return self.end_infraction(infraction)

        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            GearbotLogging.log_key(guild.id, 'tempban_already_lifted', **info)
            return self.end_infraction(infraction)

        fid = f"{guild.id}-{infraction.user_id}"
        self.bot.data["unbans"].add(fid)
        try:
            await guild.unban(user)
        except discord.Forbidden:
            self.bot.data["unbans"].remove(fid)
            GearbotLogging.log_key(guild.id, 'tempban_expired_missing_perms', **info)
        else:
            GearbotLogging.log_key(guild.id, 'tempban_lifted', **info)
        finally:
            self.end_infraction(infraction)

    def end_infraction(self, infraction):
        infraction.active = False
        infraction.save()
        self.handling.remove(infraction.id)


def setup(bot):
    bot.add_cog(Moderation(bot))
