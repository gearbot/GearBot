import asyncio
import datetime
import re
import time
import typing
from typing import Optional

import discord
from discord import Object, Emoji, Forbidden, NotFound, ActivityType, DMChannel, DiscordException
from discord.ext import commands
from discord.ext.commands import BadArgument, Greedy, MemberConverter, RoleConverter, MissingPermissions
from tortoise.exceptions import MultipleObjectsReturned
from tortoise.transactions import in_transaction

from Bot import TheRealGearBot
from Cogs.BaseCog import BaseCog
from Util import Configuration, Utils, GearbotLogging, Pages, InfractionUtils, Emoji, Translator, \
    Archive, Confirmation, MessageUtils, Questions, server_info, Actions, Permissioncheckers
from Util.Actions import ActionFailed
from Util.Converters import BannedMember, UserID, Reason, Duration, DiscordUser, PotentialID, RoleMode, Guild, \
    RangedInt, Message, RangedIntBan, VerificationLevel, Nickname, ServerMember, TranslatedBadArgument
from Util.Matchers import URL_MATCHER
from Util.Permissioncheckers import bot_has_guild_permission
from database import DBUtils
from database.DatabaseConnector import LoggedMessage, Infraction


class Moderation(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)

        self.running = True
        self.handling = set()
        self.bot.loop.create_task(self.timed_actions())
        Pages.register("roles", self.roles_init, self.roles_update)
        Pages.register("mass_failures", self._mass_failures_init, self._mass_failures_update)

        self.regexes = dict()

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
    @commands.bot_has_permissions(external_emojis=True, add_reactions=True)
    async def roles(self, ctx: commands.Context, mode: RoleMode = "hierarchy"):
        """roles_help"""
        data = {"mode": mode} if mode != "hierarchy" else {}
        await Pages.create_new(self.bot, "roles", ctx, **data)

    @commands.command()
    @commands.guild_only()
    async def seen(self, ctx, user: ServerMember):
        """seen_help"""
        messages = await LoggedMessage.filter(author=user.id, server=ctx.guild.id).order_by("-messageid").limit(1).prefetch_related("attachments")
        if len(messages) == 0:
            await MessageUtils.send_to(ctx, "SPY", "seen_fail", user_id=user.id, user=Utils.clean_user(user))
        else:
            await MessageUtils.send_to(ctx, "EYES", "seen_success", user_id=user.id, user=Utils.clean_user(user), date=Object(messages[0].messageid).created_at)
    
    @commands.group(aliases=["nick"], invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname(self, ctx: commands.Context):
        """mod_nickname_help"""
        if ctx.subcommand_passed is None:
            await ctx.invoke(self.bot.get_command("help"), query="nickname")
    
    @nickname.command("add", aliases=["set", "update", "edit"])
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname_add(self, ctx, user: ServerMember, *, nick:Nickname):
        """mod_nickname_add_help"""
        try:
            allowed, message = Actions.can_act("nickname", ctx, user)
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
        except (discord.HTTPException, AttributeError) as ex:
            await MessageUtils.send_to(ctx, "NO", "mod_nickname_other_error", user_id=user.id, user=Utils.clean_user(user), error=ex.text)

    @nickname.command("remove", aliases=["clear", "nuke", "reset"])
    @commands.bot_has_permissions(manage_nicknames=True)
    async def nickname_remove(self, ctx, user: ServerMember):
        """mod_nickname_remove_help"""
        if user.nick is None:
            await MessageUtils.send_to(ctx, "WHAT", "mod_nickname_mia", user=Utils.clean_user(user))
            return
        allowed, message = Actions.can_act("nickname", ctx, user)
        if allowed:
            self.bot.data["nickname_changes"].add(f"{user.guild.id}-{user.id}")

            mod_name = Utils.clean_name(ctx.author)
            before_clean = Utils.clean_name(user.nick)
            name = Utils.clean_user(user)

            await user.edit(nick=None)
            await MessageUtils.send_to(ctx, "YES", "mod_nickname_nuked", user_id=user.id, user=Utils.clean_user(user))

            GearbotLogging.log_key(
                ctx.guild.id, 
                "mod_nickname_removed", 
                user=name, 
                user_id=user.id,
                before=before_clean, 
                moderator=mod_name,
                moderator_id=ctx.author.id
            )
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)


    @commands.group(invoke_without_command=True)
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
            if len(roles) == 1:
                drole = roles[0]
            elif len(roles) > 1:
                await MessageUtils.send_to(ctx, "NO", "role_too_many_matches", name=role.replace("@", "@\u200b"))
                return
            else:
                await MessageUtils.send_to(ctx, "NO", "role_no_matches", name=role.replace("@", "@\u200b"))
                return

        if Actions.can_act(f"role_{action}", ctx, user):
            role_list = Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST")
            mode = Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE")
            mode_name = "allow" if mode else "block"
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
    async def add(self, ctx, user: ServerMember, *, role: str):
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
    async def kick(self, ctx, user: ServerMember, *, reason: Reason = ""):
        """kick_help"""
        reason = Utils.enrich_reason(ctx, reason)

        await Actions.act(ctx, "kick", user.id, self._kick, reason=reason, message=True)
                    
    async def _kick(self, ctx, user, reason, message, dm_action=True):
        await self.bot.redis_pool.psetex(f"forced_exits:{ctx.guild.id}-{user.id}", 8000, "1")

        if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_KICK") and dm_action:
            await Utils.send_infraction(self.bot, user, ctx.guild, 'BOOT', 'kick', reason)
        
        await ctx.guild.kick(user,
                             reason=Utils.trim_message(
                                 f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}",
                                 500))
        i = await InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, 'Kick', reason, active=False)
        GearbotLogging.log_key(ctx.guild.id, 'kick_log', user=Utils.clean_user(user), user_id=user.id,
                               moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id,
                               reason=reason, inf=i.id)                    
        if message:
            await MessageUtils.send_to(ctx, "YES", "kick_confirmation", ctx.guild.id, user=Utils.clean_user(user),
                                       user_id=user.id, reason=reason, inf=i.id)

    @commands.guild_only()
    @commands.command("mkick", aliases=["👢👢"])
    @commands.bot_has_permissions(kick_members=True, add_reactions=True, external_emojis=True)
    async def mkick(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """mkick_help"""
        reason = Utils.enrich_reason(ctx, reason)

        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
            failures = await Actions.mass_action(ctx, "kick", targets, self._kick, reason=reason, message=False, dm_action=Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_KICK"))
            await pmessage.delete()
            await MessageUtils.send_to(ctx, "YES", "mkick_confirmation", count=len(targets) - len(failures))
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action_type="kick",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))

        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("mkick_confirm", ctx), on_yes=yes)
        else:
            await Utils.empty_list(ctx, "kick")

    @staticmethod
    async def _mass_failures_init(ctx, action_type, failures):
        failures = failures.split("----NEW PAGE----")
        return f"**{Translator.translate(f'mass_failures_{action_type}', ctx, page_num=1, pages=len(failures))}**```\n{failures[0]}```", None, len(failures) > 1

    @staticmethod
    async def _mass_failures_update(ctx, message, page_num, action_type, data):
        page, page_num = Pages.basic_pages(data["failures"].split("----NEW PAGE----"), page_num, action_type)
        action_type = data["action_type"]
        data["page"] = page_num
        return f"**{Translator.translate(f'mass_failures_{action_type}', ctx, page_num=page_num + 1, pages=len(data['failures']))}**```\n{page}```", None, data

    @commands.guild_only()
    @commands.command()
    @commands.bot_has_permissions(external_emojis=True, add_reactions=True)
    async def bean(self, ctx, user: ServerMember, *, reason: Reason = ""):
        """bean_help"""
        reason = Utils.enrich_reason(ctx, reason)

        allowed, message = Actions.can_act("bean", ctx, user)
        if allowed:
            await MessageUtils.send_to(ctx, "YES", "bean_confirmation", user=Utils.clean_user(user), user_id=user.id, reason=reason)
            try :
                message = await self.bot.wait_for("message", timeout=60*5, check=lambda m: m.author == user and m.channel.guild == ctx.guild and m.channel.permissions_for(m.guild.me).add_reactions)
            except asyncio.TimeoutError:
                pass
            else:
                try:
                    await message.add_reaction(Emoji.get_emoji('BEAN'))
                except (Forbidden, NotFound):
                    await message.channel.send(Emoji.get_chat_emoji('BEAN'))
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    @commands.command(aliases=["🚪"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True, add_reactions=True, external_emojis=True)
    async def ban(self, ctx: commands.Context, user: DiscordUser, *, reason: Reason = ""):
        """ban_help"""

        member = await Utils.get_member(ctx.bot, ctx.guild, user.id)
        if member is not None:
            await self._ban_command(ctx, member, reason, 0)
        else:

            try:
                await ctx.guild.fetch_ban(user)
            except NotFound:
                async def yes():
                    await ctx.invoke(self.forceban, user=user, reason=reason)

                await Confirmation.confirm(ctx, MessageUtils.assemble(ctx, "SINISTER", 'ban_user_not_here', user=Utils.clean_user(user)), on_yes=yes)
            else:
                await MessageUtils.send_to(ctx, 'BAD_USER', 'already_banned_user')


    @commands.command(aliases=["clean_ban"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True, add_reactions=True, external_emojis=True)
    async def cleanban(self, ctx: commands.Context, user: DiscordUser, days: Optional[RangedIntBan]=1, *, reason: Reason = ""):
        """clean_ban_help"""
        await self._ban_command(ctx, user, reason, days)

    async def _ban_command(self, ctx, user, reason, days):
        member = await Utils.get_member(ctx.bot, ctx.guild, user.id)

        reason = Utils.enrich_reason(ctx, reason)

        allowed, message = Actions.can_act("ban", ctx, member)
        if allowed:
            await self._ban(ctx, user, reason, True, days=days)
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True, add_reactions=True, external_emojis=True)
    async def tempban(self, ctx: commands.Context, user: DiscordUser, duration: Duration, *, reason: Reason = ""):
        """tempban_help"""
        if duration.unit is None:
            parts = reason.split(" ")
            duration.unit = parts[0]
            reason = " ".join(parts[1:])

        reason = Utils.enrich_reason(ctx, reason)

        member = await Utils.get_member(self.bot, ctx.guild, user.id)
        if member is not None:
            allowed, message = Actions.can_act("ban", ctx, member)
        else:
            allowed = True
        if allowed:
            duration_seconds = duration.to_seconds(ctx)
            if duration_seconds > 0:
                if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_TEMPBAN"):
                    dur=f'{duration.length}{duration.unit}'
                    await Utils.send_infraction(self.bot, user, ctx.guild, 'BAN', 'tempban', reason, duration=dur)
                await self.bot.redis_pool.psetex(f"forced_exits:{ctx.guild.id}-{user.id}", 8000, "1")
                await ctx.guild.ban(user, reason=Utils.trim_message(
                    f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                                    delete_message_days=0)


                until = time.time() + duration_seconds
                async with in_transaction():
                    await Infraction.filter(user_id=user.id, type="Tempban", guild_id=ctx.guild.id).update(active=False)
                    i = await InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Tempban", reason, end=until)
                GearbotLogging.log_key(ctx.guild.id, 'tempban_log', user=Utils.clean_user(user), user_id=user.id,
                                       moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason,
                                       until=datetime.datetime.utcfromtimestamp(until), inf=i.id)
                await MessageUtils.send_to(ctx, "YES", "tempban_confirmation", user=Utils.clean_user(user),
                                             user_id=user.id, reason=reason,
                                             until=datetime.datetime.utcfromtimestamp(until), inf=i.id)
        else:
            await MessageUtils.send_to(ctx, "NO", message, translate=False)

    async def _ban(self, ctx, user, reason, confirm, days=0, dm_action=True):
        await self.bot.redis_pool.psetex(f"forced_exits:{ctx.guild.id}-{user.id}", 8000, "1")
                            
        if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_BAN") and dm_action:
            await Utils.send_infraction(self.bot, user, ctx.guild, 'BAN', 'ban', reason)
                    
        await ctx.guild.ban(user, reason=Utils.trim_message(
            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                            delete_message_days=days)
        await Infraction.filter(user_id=user.id, type="Unban", guild_id=ctx.guild.id).update(active=False)
        i = await InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Ban", reason)
        GearbotLogging.log_key(ctx.guild.id, 'ban_log', user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason, inf=i.id)
        if confirm:
            await MessageUtils.send_to(ctx, "YES", "ban_confirmation", user=Utils.clean_user(user), user_id=user.id,
                                         reason=reason, inf=i.id)

    async def _unban(self, ctx, user, reason, confirm, dm_action=False):
        self.bot.data["unbans"].add(f"{ctx.guild.id}-{user.id}")
        try:
            await ctx.guild.unban(user, reason=Utils.trim_message(
                f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500))
        except NotFound:
            ban_not_found = Translator.translate("ban_not_found", ctx)
            raise ActionFailed(f"{ban_not_found}")
        except Forbidden:
            ban_not_found = Translator.translate("unban_forbidden", ctx)
            raise ActionFailed(f"{ban_not_found}")
        else:
            await Infraction.filter(user_id=user.id, type__in=["Ban", "Tempban"], guild_id=ctx.guild.id).update(active=False)
            i = await InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Unban", reason)
            GearbotLogging.log_key(ctx.guild.id, 'unban_log', user=Utils.clean_user(user), user_id=user.id, moderator=Utils.clean_user(ctx.author),
                                    moderator_id=ctx.author.id, reason=reason, inf=i.id)
        if confirm:
            await MessageUtils.send_to(ctx, "YES", "unban_confirmation", user=Utils.clean_user(user), user_id=user.id,
                                         reason=reason, inf=i.id)

    @commands.guild_only()
    @commands.command(aliases=["🚪🚪"])
    @commands.bot_has_permissions(ban_members=True, add_reactions=True, external_emojis=True)
    async def mban(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """mban_help"""
        reason = Utils.enrich_reason(ctx, reason)

        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
            failures = await Actions.mass_action(ctx, "ban", targets, self._ban, reason=reason, confirm=False, require_on_server=False, dm_action=Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_BAN"))
            await pmessage.delete()
            await MessageUtils.send_to(ctx, "YES", "mban_confirmation", count=len(targets) - len(failures))
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action_type="ban",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))
        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("mban_confirm", ctx), on_yes=yes)
        else:
            await Utils.empty_list(ctx, "ban")

    @commands.guild_only()
    @commands.command()
    @commands.bot_has_permissions(ban_members=True, add_reactions=True, external_emojis=True)
    async def munban(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """munban_help"""
        reason = Utils.enrich_reason(ctx, reason)

        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
            failures = await Actions.mass_action(ctx, "unban", targets, self._unban, reason=reason, require_on_server=False, confirm=False, check_bot_ability=False, dm_action=False)
            await pmessage.delete()
            await MessageUtils.send_to(ctx, "YES", "munban_confirmation", count=len(targets) - len(failures))
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action_type="unban",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))
        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("munban_confirm", ctx), on_yes=yes)
        else:
            await Utils.empty_list(ctx, "unban")
    
    @commands.guild_only()
    @commands.command(aliases=["mcb"])
    @commands.bot_has_permissions(ban_members=True, add_reactions=True, external_emojis=True)
    async def mcleanban(self, ctx, targets: Greedy[PotentialID], days: Optional[RangedIntBan]=1, *, reason: Reason = ""):
        """mcleanban_help"""
        reason = Utils.enrich_reason(ctx, reason)
        
        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
            valid = 0
            failures = []
            filtered = []
            for t in targets:
                if t not in filtered: 
                    filtered.append(t)
                else:
                    await MessageUtils.send_to(ctx, "NO", "mcleanban_duplicates", t=t)
            for f in filtered:
                try:
                    member = await MemberConverter().convert(ctx, str(f))
                except BadArgument:
                    try:
                        user = await DiscordUser().convert(ctx, str(f))
                    except BadArgument as bad:
                        failures.append(f"{f}: {bad}")
                    else:
                        await self._ban(ctx, user, reason, True, days=days)
                        valid += 1
                else:
                    allowed, message = Actions.can_act("ban", ctx, member)
                    if allowed:
                        await self._ban(ctx, member, reason, True, days=days)
                        valid += 1
                    else:
                        failures.append(f"{f}: {message}")
            await pmessage.delete()
            await MessageUtils.send_to(ctx, "YES", "mcleanban_confirmation", count=valid)
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action_type="ban",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))
        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("mcleanban_confirm", ctx), on_yes=yes)
        else:
            await Utils.empty_list(ctx, "ban")

    @commands.command(aliases=["softban"])
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    async def cleankick(self, ctx: commands.Context, user: ServerMember, *, reason: Reason = ""):
        """softban_help"""
        reason = Utils.enrich_reason(ctx, reason)

        allowed, message = Actions.can_act("softban", ctx, user)
        if allowed:
            await self.bot.redis_pool.psetex(f"forced_exits:{ctx.guild.id}-{user.id}", 8000, "1")
            self.bot.data["unbans"].add(f"{ctx.guild.id}-{user.id}")
            i = await InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Softban", reason, active=False)
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
        reason = Utils.enrich_reason(ctx, reason)
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
    @commands.bot_has_permissions(ban_members=True, add_reactions=True, external_emojis=True)
    async def forceban(self, ctx: commands.Context, user: DiscordUser, *, reason: Reason = ""):
        """forceban_help"""
        reason = Utils.enrich_reason(ctx, reason)
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
                await MessageUtils.send_to(ctx, 'BAD_USER', 'already_banned_user')

        else:
            # they are here, reroute to regular ban
            await MessageUtils.send_to(ctx, 'WARNING', 'forceban_to_ban', user=Utils.clean_user(member))
            await ctx.invoke(self.ban, member, reason=reason)

    async def _forceban(self, ctx, user, reason):
        # not banned, wack with the hammer
        if user.discriminator == '0000':
            await MessageUtils.send_to(ctx, 'NO', 'forceban_unable_sytem_user')
            return

        await self.bot.redis_pool.psetex(f"forced_exits:{ctx.guild.id}-{user.id}", 8000, "1")
        await ctx.guild.ban(user, reason=Utils.trim_message(
            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500),
                            delete_message_days=0)
        await Infraction.filter(user_id=user.id, type__in=["Unban", "Tempban"], guild_id=ctx.guild.id).update(active=False)
        i = await InfractionUtils.add_infraction(ctx.guild.id, user.id, ctx.author.id, "Forced ban", reason)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('forceban_confirmation', ctx.guild.id, user=Utils.clean_user(user), user_id=user.id, reason=reason, inf=i.id)}")
        GearbotLogging.log_key(ctx.guild.id, 'forceban_log', user=Utils.clean_user(user), user_id=user.id,
                               moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason,
                               inf=i.id)

        # check for pending tembans
        tempbans = await Infraction.filter(user_id = user.id, type = "Tempban", guild_id = ctx.guild.id, active=True)
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
        reason = Utils.enrich_reason(ctx, reason)
        fid = f"{ctx.guild.id}-{member.user.id}"
        self.bot.data["unbans"].add(fid)
        try:
            await ctx.guild.unban(member.user, reason=Utils.trim_message(
                f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}", 500))
        except Exception as e:
            if fid in self.bot.data["unbans"]:
                self.bot.data["unbans"].remove(fid)
            raise e
        await Infraction.filter(user_id=member.user.id, type__in=["Ban", "Tempban"], guild_id=ctx.guild.id).update(active=False)
        i = await InfractionUtils.add_infraction(ctx.guild.id, member.user.id, ctx.author.id, "Unban", reason)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('unban_confirmation', ctx.guild.id, user=Utils.clean_user(member.user), user_id=member.user.id, reason=reason, inf = i.id)}")
        GearbotLogging.log_key(ctx.guild.id, 'unban_log', user=Utils.clean_user(member.user), user_id=member.user.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason, inf=i.id)


    @commands.command()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(add_reactions=True, external_emojis=True)
    async def mmute(self, ctx, targets: Greedy[PotentialID], duration: Duration, *, reason: Reason = ""):
        """mmute_help"""
        if duration.unit is None:
            parts = reason.split(" ")
            duration.unit = parts[0]
            reason = " ".join(parts[1:])
        reason = Utils.enrich_reason(ctx, reason)
        roleid = Configuration.get_var(ctx.guild.id, "ROLES", "MUTE_ROLE")
        if roleid == 0:
            await ctx.send(
                f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mmute_not_configured', ctx.guild.id)}")
        else:
            role = ctx.guild.get_role(roleid)
            if role is None:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_role_missing', ctx.guild.id)}")
            else:
                async def yes():
                    pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")

                    failures = await Actions.mass_action(ctx, "mute", targets, self._mmute, reason=reason, dm_action=len(targets) < 6 and Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_MUTE"), role=role, duration=duration)

                    await pmessage.delete()
                    await MessageUtils.send_to(ctx, "YES", "mmute_confirmation", count=len(targets) - len(failures))
                    if len(failures) > 0:
                        await Pages.create_new(self.bot, "mass_failures", ctx, action_type="mute",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))

                if len(targets) > 0:
                    await Confirmation.confirm(ctx, Translator.translate("mmute_confirm", ctx, count=len(targets)), on_yes=yes)
                else:
                    await Utils.empty_list(ctx, "mute")

    async def _mmute(self, ctx, target, *, reason, role, duration, dm_action=True):
        infraction = None
        try:
            infraction = await Infraction.get_or_none(user_id = target.id, type = "Mute", guild_id = ctx.guild.id, active=True)
        except MultipleObjectsReturned:
            pass

        if infraction is not None:
            ban_not_found = Translator.translate("already_muted", ctx)
            raise ActionFailed(f"{ban_not_found}")

        await target.add_roles(role, reason=Utils.trim_message(
            f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}",
            500))
        if target.voice and target.voice.channel:
            permissions = target.voice.channel.permissions_for(ctx.guild.me)
            if permissions.move_members:
                await target.move_to(None, reason=f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}")
        until = time.time() + duration.to_seconds(ctx)
        i = await InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Mute", reason,
                                                 end=until)

        GearbotLogging.log_key(ctx.guild.id, 'mute_log',
                               user=Utils.clean_user(target),
                               user_id=target.id,
                               moderator=Utils.clean_user(ctx.author),
                               moderator_id=ctx.author.id,
                               duration=f'{duration.length} {duration.unit}',
                               reason=reason, inf=i.id)
        if dm_action:
            dur=f'{duration.length}{duration.unit}'
            await Utils.send_infraction(self.bot, target, ctx.guild, 'MUTE', 'mute', reason, duration=dur)



    @commands.command()
    @commands.bot_has_guild_permissions(manage_roles=True)
    @commands.bot_has_permissions(add_reactions=True, external_emojis=True)
    async def mute(self, ctx: commands.Context, target: ServerMember, duration: Duration, *, reason: Reason = ""):
        """mute_help"""
        if duration.unit is None:
            parts = reason.split(" ")
            duration.unit = parts[0]
            reason = " ".join(parts[1:])
        reason = Utils.enrich_reason(ctx, reason)
        roleid = Configuration.get_var(ctx.guild.id, "ROLES", "MUTE_ROLE")
        if roleid == 0:
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
                            try:
                                infraction = await Infraction.get_or_none(user_id = target.id, type = "Mute", guild_id = ctx.guild.id, active=True)
                            except MultipleObjectsReturned:
                                infraction = await Infraction.filter(user_id = target.id, type = "Mute", guild_id = ctx.guild.id, active=True).first()
                                await Infraction.filter(user_id = target.id, type = "Mute", guild_id = ctx.guild.id, active=True, id__not=infraction.id).update(active=False)
                                await MessageUtils.send_to(ctx, "BUG", "CRITICAL ERROR: This user somehow has multiple active mutes, this should not be possible. The older corrupted mutes have been deactived and this command used only the most recent one to work. Please let me know about this on the support server (link found in the about command or website) for further investigation!",translate=False)

                            if infraction is None:
                                await target.add_roles(role, reason=Utils.trim_message(
                                    f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}",
                                    500))
                                if target.voice:
                                    permissions = target.voice.channel.permissions_for(ctx.guild.me)
                                    if permissions.move_members:
                                        await target.move_to(None, reason=f"Moderator: {ctx.author.name}#{ctx.author.discriminator} ({ctx.author.id}) Reason: {reason}")
                                until = time.time() + duration_seconds
                                i = await InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Mute", reason,
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
                                if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_MUTE"):
                                    dur=f'{duration.length}{duration.unit}'
                                    await Utils.send_infraction(self.bot, target, ctx.guild, 'MUTE', 'mute', reason, duration=dur)
                            else:
                                d = f'{duration.length} {duration.unit}'
                                async def extend():
                                    infraction.end += duration_seconds
                                    await infraction.save()
                                    await MessageUtils.send_to(ctx, 'YES', 'mute_duration_extended', duration=d, end=infraction.end)
                                    GearbotLogging.log_key(ctx.guild.id, 'mute_duration_extended_log', user=Utils.clean_user(target),
                                                           user_id=target.id,
                                                           moderator=Utils.clean_user(ctx.author),
                                                           moderator_id=ctx.author.id,
                                                           duration=f'{duration.length} {duration.unit}',
                                                           reason=reason, inf_id=infraction.id, end=datetime.datetime.utcfromtimestamp(infraction.end).strftime('%Y-%m-%d %H:%M:%S'))
                                    name = Utils.clean_user(target)
                                    if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_MUTE"):
                                        try:
                                            dur=f'{duration.length}{duration.unit}'
                                            await target.send(
                                                f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('extend_mute_dm', ctx.guild.id, server=ctx.guild.name, duration=dur, guild_id=ctx.guild.id)}```{reason}```")
                                        except (discord.HTTPException, AttributeError):
                                            GearbotLogging.log_key(ctx.guild.id, 'mute_could_not_dm', user=name,
                                                                userid=target.id)

                                async def until():
                                    infraction.end = time.time() + duration_seconds
                                    await infraction.save()
                                    await MessageUtils.send_to(ctx, 'YES', 'mute_duration_added', duration=d)
                                    GearbotLogging.log_key(ctx.guild.id, 'mute_duration_added_log',
                                                           user=Utils.clean_user(target),
                                                           user_id=target.id,
                                                           moderator=Utils.clean_user(ctx.author),
                                                           moderator_id=ctx.author.id,
                                                           duration=f'{duration.length} {duration.unit}',
                                                           reason=reason, inf_id=infraction.id, end=datetime.datetime.utcfromtimestamp(infraction.end).strftime('%Y-%m-%d %H:%M:%S'))
                                    name = Utils.clean_user(target)
                                    if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_MUTE"):
                                        try: 
                                            dur=f'{duration.length}{duration.unit}'
                                            await target.send(
                                                f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_duration_until_dm', ctx.guild.id, server=ctx.guild.name, duration=dur, guild_id=ctx.guild.id)}```{reason}```")
                                        except (discord.HTTPException, AttributeError):
                                            GearbotLogging.log_key(ctx.guild.id, 'mute_could_not_dm', user=name,
                                                                userid=target.id)

                                async def overwrite():
                                    infraction.end = infraction.start + duration_seconds
                                    await infraction.save()
                                    await MessageUtils.send_to(ctx, 'YES', 'mute_duration_overwritten', duration=d, end=infraction.end)
                                    GearbotLogging.log_key(ctx.guild.id, 'mute_duration_overwritten_log',
                                                           user=Utils.clean_user(target),
                                                           user_id=target.id,
                                                           moderator=Utils.clean_user(ctx.author),
                                                           moderator_id=ctx.author.id,
                                                           duration=f'{duration.length} {duration.unit}',
                                                           reason=reason, inf_id=infraction.id, end=infraction.end)
                                    name = Utils.clean_user(target)
                                    if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_MUTE"):
                                        try:
                                            dur=f'{duration.length}{duration.unit}'
                                            await target.send(
                                                f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('mute_duration_change_dm', ctx.guild.id, server=ctx.guild.name, duration=dur, guild_id=ctx.guild.id)}```{reason}```")
                                        except (discord.HTTPException, AttributeError):
                                            GearbotLogging.log_key(ctx.guild.id, 'mute_could_not_dm', user=name,
                                                                userid=target.id)

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


    @commands.guild_only()
    @commands.command()
    @bot_has_guild_permission(manage_roles=True)
    @commands.bot_has_permissions(add_reactions=True, external_emojis=True)
    async def munmute(self, ctx, targets: Greedy[PotentialID], *, reason: Reason = ""):
        """munmute_help"""
        reason = Utils.enrich_reason(ctx, reason)

        async def yes():
            pmessage = await MessageUtils.send_to(ctx, "REFRESH", "processing")
            failures = await Actions.mass_action(ctx, "unmute", targets, self._unmute, reason=reason, require_on_server=True, dm_action=Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_UNMUTE"))
            await pmessage.delete()
            await MessageUtils.send_to(ctx, "YES", "munmute_confirmation", count=len(targets) - len(failures))
            if len(failures) > 0:
                await Pages.create_new(self.bot, "mass_failures", ctx, action_type="unmute",
                                       failures="----NEW PAGE----".join(Pages.paginate("\n".join(failures))))
        if len(targets) > 0:
            await Confirmation.confirm(ctx, Translator.translate("munmute_confirm", ctx), on_yes=yes)
        else:
            await Utils.empty_list(ctx, "unmute")

    @commands.command()
    @commands.guild_only()
    @bot_has_guild_permission(manage_roles=True)
    async def unmute(self, ctx: commands.Context, target: ServerMember, *, reason: Reason = ""):
        """unmute_help"""
        await self._unmute(ctx, target, reason=reason, confirm=True)

    async def _unmute(self, ctx, target, *, reason, confirm=False, dm_action=None):
        if dm_action is None:
            dm_action = Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_UNMUTE")
        reason = Utils.enrich_reason(ctx, reason)
        roleid = Configuration.get_var(ctx.guild.id, "ROLES", "MUTE_ROLE")
        if roleid == 0:
            if confirm:
                await MessageUtils.send_to(ctx, 'NO', 'unmute_fail_disabled')
            else:
                raise ActionFailed(Translator.translate("unmute_fail_disabled", ctx))
        else:
            role = ctx.guild.get_role(roleid)
            if role is None:
                if confirm:
                    await MessageUtils.send_to(ctx, 'NO', 'unmute_fail_role_removed')
                    return
                else:
                    raise ActionFailed(Translator.translate("unmute_fail_role_removed", ctx))
            else:
                try:
                    infraction = await Infraction.get_or_none(user_id = target.id, type = "Mute", guild_id = ctx.guild.id, active=True)
                except MultipleObjectsReturned:
                    infraction = await Infraction.filter(user_id = target.id, type = "Mute", guild_id = ctx.guild.id, active=True).first()
                    await Infraction.filter(user_id = target.id, type = "Mute", guild_id = ctx.guild.id, active=True, id__not=infraction.id).update(active=False)
                    await MessageUtils.send_to(ctx, "BUG", "CRITICAL ERROR: This user somehow has multiple active mutes, this should not be possible. The older corrupted mutes have been deactived and this command used only the most recent one to work. Please let me know about this on the support server (link found in the about command or website) for further investigation!",translate=False)
                if role not in target.roles and infraction is None:
                    if confirm:
                        await MessageUtils.send_to(ctx, 'WHAT', 'unmute_not_muted', user=Utils.clean_user(target))
                        return
                    else:
                        raise ActionFailed(Translator.translate("unmute_not_muted", ctx, user=Utils.clean_user(target)))
                else:
                    if role.position >= ctx.me.top_role.position:
                        if confirm:
                            await MessageUtils.send_to(ctx, 'NO', 'unmute_higher_role')
                            return
                        else:
                            raise ActionFailed(Translator.translate("unmute_higher_role", ctx))
                    i = await InfractionUtils.add_infraction(ctx.guild.id, target.id, ctx.author.id, "Unmute", reason)
                    name = Utils.clean_user(target)
                    if Configuration.get_var(ctx.guild.id, "INFRACTIONS", "DM_ON_UNMUTE") and dm_action:
                        await Utils.send_infraction(self.bot, target, ctx.guild, 'INNOCENT', 'unmute', reason)
                    await Infraction.filter(user_id=target.id, type="Mute", guild_id=ctx.guild.id).update(active=False)
                    await target.remove_roles(role, reason=f"Unmuted by {ctx.author.name}, {reason}")
                    if confirm:
                        await MessageUtils.send_to(ctx, 'INNOCENT', 'unmute_confirmation', user=Utils.clean_user(target), inf = i.id)
                    GearbotLogging.log_key(ctx.guild.id, 'unmute_modlog', user=Utils.clean_user(target), user_id=target.id, moderator=Utils.clean_user(ctx.author), moderator_id=ctx.author.id, reason=reason, inf=i.id)


    @commands.command(aliases=["info"])
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx: commands.Context, *, user: DiscordUser = None):
        """userinfo_help"""
        if user is None:
            user = member = ctx.author
        else:
            member = None if ctx.guild is None else await Utils.get_member(self.bot, ctx.guild, user.id)
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
            embed.add_field(name=Translator.translate('nickname', ctx), value=Utils.escape_markdown(member.nick), inline=True)

            role_list = [role.mention for role in reversed(member.roles) if role is not ctx.guild.default_role]
            if len(role_list) > 60:
                embed.add_field(name=Translator.translate('all_roles', ctx), value=Translator.translate('too_many_many_roles', ctx), inline=False)
            elif len(role_list) > 40:
                embed.add_field(name=Translator.translate('all_roles', ctx), value=Translator.translate('too_many_roles', ctx), inline=False)
            elif len(role_list) > 0:
                embed.add_field(name=Translator.translate('all_roles', ctx), value=" ".join(role_list), inline=False)
            else:
                embed.add_field(name=Translator.translate('all_roles', ctx), value=Translator.translate("no_roles", ctx), inline=False)

            embed.add_field(name=Translator.translate('joined_at', ctx),
                            value=f"{(ctx.message.created_at - member.joined_at).days} days ago (``{member.joined_at}``)",
                            inline=True)
        embed.add_field(name=Translator.translate('account_created_at', ctx),
                        value=f"{(ctx.message.created_at - user.created_at).days} days ago (``{user.created_at}``)",
                        inline=True)
        infs = ""
        if Configuration.get_master_var("global_inf_counter", True):
            infractions = await Infraction.filter(user_id=user.id, type__not="Note")
            il = len(infractions)
            seen = []
            ild = 0
            for i in infractions:
                if i.guild_id not in seen:
                    seen.append(i.guild_id)
                ild += 1
            emoji = "SINISTER" if il >= 2 else "INNOCENT"
            infs += MessageUtils.assemble(ctx, emoji, "total_infractions", total=il, servers=ild) + "\n"

        infractions = await Infraction.filter(user_id=user.id, guild_id=ctx.guild.id, type__not="Note")
        emoji = "SINISTER" if len(infractions) >= 2 else "INNOCENT"
        embed.add_field(name=Translator.translate("infractions", ctx),
                        value=infs + MessageUtils.assemble(ctx, emoji, "guild_infractions", count=len(infractions)))

        await ctx.send(embed=embed)

    @commands.command(aliases=["server"])
    @commands.bot_has_permissions(embed_links=True)
    async def serverinfo(self, ctx, guild: Guild = None):
        """serverinfo_help"""
        if guild is None:
            guild = ctx.guild
        embed = server_info.server_info_embed(guild, ctx.guild)
        embed.set_footer(text=Translator.translate('requested_by', ctx, user=ctx.author),
                         icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.group(invoke_without_command=True)
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
        else:
            permissions = channel.permissions_for(ctx.author)
            if not permissions.read_messages:
                await MessageUtils.send_to(ctx, 'NO', 'archive_leak_denied')
                return
        if Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", "ENABLED"):
            await MessageUtils.send_to(ctx, 'SEARCH', 'searching_archives')
            messages = await LoggedMessage.filter(server=ctx.guild.id, channel=channel.id).order_by("-messageid").limit(amount).prefetch_related("attachments")
            await Archive.ship_messages(ctx, messages + DBUtils.get_messages_for_channel(channel.id), "channel")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_no_edit_logs', ctx)}")

    @archive.command()
    async def user(self, ctx, user: DiscordUser, amount=100):
        """archive_user_help"""
        user = user.id
        if amount > 5000:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_too_much', ctx)}")
            return
        if Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", "ENABLED"):
            await MessageUtils.send_to(ctx, 'SEARCH', 'searching_archives')
            messages = await LoggedMessage.filter(server=ctx.guild.id, author=user).order_by("-messageid").limit(amount).prefetch_related("attachments")
            filtered = False
            actual_messages = []
            for message in messages + DBUtils.get_messages_for_user_in_guild(user, ctx.guild.id):
                channel = ctx.bot.get_channel(message.channel)
                if channel is None or channel.permissions_for(ctx.author).read_messages:
                    actual_messages.append(message)
                else:
                    filtered=True
            await Archive.ship_messages(ctx, actual_messages, "user", filtered=filtered)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('archive_no_edit_logs', ctx)}")

    @commands.group(invoke_without_command=True)
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
        if len(users) == 0:
            await MessageUtils.send_to(ctx, 'NO', 'clean_missing_targets')
            return
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


    @clean.command("links")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_links(self, ctx, amount: RangedInt(1, 5000)):
        """clean_links_help"""
        await self._clean(ctx, amount, lambda m: len(URL_MATCHER.findall(m.content)) > 1)


    @clean.command("containing")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_containing(self, ctx, text:str, amount: RangedInt(1, 5000)=100):
        """clean_containing_help"""
        await self._clean(ctx, amount, lambda m: text in m.content)

    @clean.command("everywhere")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_messages=True)
    async def clean_everywhere(self, ctx, users: Greedy[DiscordUser], amount: RangedInt(1) = 50):
        """clean_everywhere_help"""
        if len(users) == 0:
            await MessageUtils.send_to(ctx, 'NO', 'clean_missing_targets')
            return
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
            except Forbidden:
                raise MissingPermissions("manage_messages")  # no clue how we got here, but we did
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
        # sleep a little, sometimes discord sends the event too soon
        await asyncio.sleep(5)
        guild: discord.Guild = channel.guild
        roleid = Configuration.get_var(guild.id, "ROLES", "MUTE_ROLE")
        if roleid != 0:
            role = guild.get_role(roleid)
            if role is not None and channel.permissions_for(guild.me).manage_channels:
                if isinstance(channel, discord.TextChannel):
                    try:
                        await channel.set_permissions(role, reason=Translator.translate('mute_setup', guild.id),
                                                      send_messages=False,
                                                      add_reactions=False)
                    except (discord.Forbidden, discord.NotFound):
                        pass
                else:
                    try:
                        await channel.set_permissions(role, reason=Translator.translate('mute_setup', guild.id),
                                                      speak=False, connect=False)
                    except (discord.Forbidden, discord.NotFound):
                        pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        now = time.time()
        i = await Infraction.get_or_none(type = "Mute", active = True, end__gt=now, guild_id = member.guild.id, user_id = member.id)
        if i is not None:
            roleid = Configuration.get_var(member.guild.id, "ROLES", "MUTE_ROLE")
            if roleid != 0:
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
            now = time.time()
            limit = time.time() + 30
            for name, action in types.items():

                for infraction in await Infraction.filter(type = name, active = True, end__lt=limit):
                    if infraction.id not in self.handling and ((infraction.guild_id >> 22) % self.bot.total_shards) in self.bot.shard_ids:
                        self.handling.add(infraction.id)
                        self.bot.loop.create_task(
                            self.run_after(infraction.end - now, action(infraction)))
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
            return await self.end_infraction(infraction)

        role = Configuration.get_var(guild.id, "ROLES", "MUTE_ROLE")
        member = await Utils.get_member(self.bot, guild, infraction.user_id)
        role = guild.get_role(role)
        if role is None or member is None:
            return await self.end_infraction(infraction)  # role got removed or member left

        info = {
            "user": Utils.clean_user(member),
            "user_id": infraction.user_id,
            "inf_id": infraction.id
        }

        if role not in member.roles:
            GearbotLogging.log_key(guild.id, 'mute_role_already_removed', **info)
            return await self.end_infraction(infraction)

        if not guild.me.guild_permissions.manage_roles:
            GearbotLogging.log_key(guild.id, "unmute_missing_perms", **info)
            return await self.end_infraction(infraction)

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
            await self.end_infraction(infraction)

    async def _lift_tempban(self, infraction):
        guild = self.bot.get_guild(infraction.guild_id)
        if guild is None:
            GearbotLogging.info(
                f"Got an expired tempban for server {infraction.guild_id} but am no longer on that server")
            return await self.end_infraction(infraction)

        user = await Utils.get_user(infraction.user_id)
        info = {
            "user": Utils.clean_user(user),
            "user_id": infraction.user_id,
            "inf_id": infraction.id
        }

        if not guild.me.guild_permissions.ban_members:
            GearbotLogging.log_key(guild.id, 'tempban_expired_missing_perms', **info)
            return await self.end_infraction(infraction)

        try:
            await guild.fetch_ban(user)
        except discord.NotFound:
            GearbotLogging.log_key(guild.id, 'tempban_already_lifted', **info)
            return await self.end_infraction(infraction)

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
            await self.end_infraction(infraction)

    async def end_infraction(self, infraction):
        infraction.active = False
        await infraction.save()
        self.handling.remove(infraction.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        pipeline = self.bot.redis_pool.pipeline()
        pipeline.hmset_dict(f"users:{member.id}",
                            name=member.name,
                            id=member.id,
                            discriminator=member.discriminator,
                            bot=int(member.bot),
                            avatar_url=str(member.avatar_url),
                            created_at=member.created_at.timestamp(),
                            is_avatar_animated=int(member.is_avatar_animated()),
                            mention=member.mention
                            )

        pipeline.expire(f"users:{member.id}", 3000)  # 5 minute cache life

        await pipeline.execute()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.webhook_id is not None or message.channel is None or isinstance(message.channel, DMChannel) or self.bot.user.id == message.author.id:
            return
        if message.channel.guild is not None:
            await self.check_for_flagged_words(message.content, message.channel.guild.id, message.channel.id, message.id, message.author, edited=False)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent):
        channel = self.bot.get_channel(int(event.data["channel_id"]))
        if channel is None or isinstance(channel, DMChannel) or "content" not in event.data:
            return
        await self.check_for_flagged_words(event.data["content"], channel.guild.id, channel.id, event.message_id, edited=True)

    async def check_for_flagged_words(self, content, guild_id, channel_id, message_id, author=None, *, edited):
        if content is None:
            return
        content = content.lower()
        token_list = Configuration.get_var(guild_id, "FLAGGING", "TOKEN_LIST")
        word_list = Configuration.get_var(guild_id, "FLAGGING", "WORD_LIST")

        for bad in (t.lower() for t in token_list):
            if bad in content:
                await self.flag_message(content, bad, guild_id, channel_id, message_id, author, "token")
                return

        if len(word_list) > 0:
            if guild_id not in self.regexes:
                regex = re.compile(r"\b(" + '|'.join(re.escape(word) for word in word_list) + r")\b", re.IGNORECASE)
                self.regexes[guild_id] = regex
            else:
                regex = self.regexes[guild_id]
            match = regex.findall(content)
            if len(match):
                await self.flag_message(content, match[0], guild_id, channel_id, message_id, author, "word")
                return

    async def flag_message(self, content, flagged, guild_id, channel_id, message_id, author=None, type=""):
        if Configuration.get_var(guild_id, "FLAGGING", "TRUSTED_BYPASS") and Permissioncheckers.is_trusted(author):
            return
        if author is None:
            message = await MessageUtils.get_message_data(self.bot, message_id)
            if message is None:
                try:
                    channel = self.bot.get_channel(channel_id)
                    message = await channel.fetch_message(message_id)
                except DiscordException:
                    pass
            if message is not None:
                author = await Utils.get_member(self.bot, self.bot.get_guild(guild_id), message.author)
        if author is None or author.id == self.bot.user.id or Permissioncheckers.get_user_lvl(author.guild, author) >= 2:
            return

        content = Utils.trim_message(content, 1700)
        content = Utils.replace_lookalikes(content)
        link = MessageUtils.construct_jumplink(guild_id, channel_id, message_id)
        GearbotLogging.log_key(guild_id, f"flagged_{type}", user=Utils.clean_user(author), user_id=author.id, flagged=flagged, channel=f"<#{channel_id}>", content=content, link=link)


def setup(bot):
    bot.add_cog(Moderation(bot))
