import asyncio
import io
import typing

import disnake
import pytz
from disnake import TextChannel, Interaction
from disnake.ext import commands
from disnake.ext.commands import BucketType
from pytz import UnknownTimeZoneError

from Cogs.BaseCog import BaseCog
from Util import Configuration, Permissioncheckers, Emoji, Translator, Features, Utils, Pages, \
    MessageUtils, Selfroles
from Util.Converters import LoggingChannel, ListMode, SpamType, RangedInt, Duration, AntiSpamPunishment
from database.DatabaseConnector import Infraction
from views import SimplePager
from views.Confirm import Confirm


class ServerHolder(object):
    sid = None
    name = None

    def __init__(self, sid):
        self.id = sid
        self.name = sid


async def add_item(ctx, item, item_type, list_name="roles", config_section="PERMISSIONS"):
    target = f"{item_type}_{list_name}".upper()
    roles = await Configuration.get_var(ctx.guild.id, config_section, target)
    sname = list_name[:-1] if list_name[-1:] == "s" else list_name
    if item == ctx.guild.default_role:
        return await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'default_role_forbidden', ctx)}")
    if item.id in roles:
        await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'already_{item_type}_{sname}', ctx, item=item.name)}")
    else:
        roles.append(item.id)
        Configuration.save(ctx.guild.id)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate(f'{item_type}_{sname}_added', ctx, item=item.name)}")


async def remove_item(ctx, item, item_type, list_name="roles", config_section="PERMISSIONS"):
    target = f"{item_type}_{list_name}".upper()
    roles = await Configuration.get_var(ctx.guild.id, config_section, target)
    sname = list_name[:-1] if list_name[-1:] == "s" else list_name
    if item.id not in roles:
        await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'was_no_{item_type}_{sname}', ctx, item=item.name)}")
    else:
        roles.remove(item.id)
        Configuration.save(ctx.guild.id)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate(f'{item_type}_{sname}_removed', ctx, item=item.name)}")


async def list_list(ctx, item_type, list_name="roles", wrapper="<@&{item}>", config_section="PERMISSIONS"):
    target = f"{item_type}_{list_name}".upper()
    items = await Configuration.get_var(ctx.guild.id, config_section, target)
    if len(items) == 0:
        desc = Translator.translate(f"no_{item_type}_{list_name}", ctx)
    else:
        desc = "\n".join(wrapper.format(item=item) for item in items)
    embed = disnake.Embed(title=Translator.translate(f"current_{item_type}_{list_name}", ctx), description=desc)
    await ctx.send(embed=embed)


def gen_override_strings(ctx, perm_dict, prefix=""):
    output = ""
    for command, d in perm_dict["commands"].items():
        lvl = d["required"]
        if lvl > -1:
            output += f"{prefix} {command}: {lvl} ({Translator.translate(f'perm_lvl_{lvl}', ctx)})\n"
        if len(d["commands"].keys()) > 0:
            output += gen_override_strings(ctx, d, f"{prefix} {command}")
    return output


class ServerAdmin(BaseCog):
    LOGGING_TYPES = [
        "RAID_LOGS",
        "CENSORED_MESSAGES",
        "MOD_ACTIONS",
        "CHANNEL_CHANGES",
        "ROLE_CHANGES",
        "MISC",
        "TRAVEL_LOGS",
        "NAME_CHANGES",
        "MESSAGE_LOGS",
        "VOICE_CHANGES_DETAILED",
        "VOICE_CHANGES",
        "SPAM_VIOLATION",
        "CONFIG_CHANGES",
        "MESSAGE_FLAGS",
        "FUTURE_LOGS",
        "FAILED_MASS_PINGS",
        "THREAD_LOGS",
        "THREAD_TRAVEL_LOGS"
    ]

    def __init__(self, bot):
        super().__init__(bot)

        bot.to_cache = []

    @commands.guild_only()
    @commands.group(aliases=["config", "cfg"], invoke_without_command=True)
    async def configure(self, ctx: commands.Context):
        """configure_help"""
        if ctx.subcommand_passed is None:
            await ctx.send("See the subcommands (!help configure) for configurations.")

    @configure.command()
    async def prefix(self, ctx: commands.Context, *, new_prefix: str = None):
        """configure_prefix_help"""
        if new_prefix is None:
            await ctx.send(
                f"{Translator.translate('current_server_prefix', ctx, prefix=await Configuration.get_var(ctx.guild.id, 'GENERAL', 'PREFIX'))}")
        elif len(new_prefix) > 25:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('prefix_too_long', ctx)}")
        else:
            Configuration.set_var(ctx.guild.id, "GENERAL", "PREFIX", new_prefix)
            await ctx.send(
                f"{Emoji.get_chat_emoji('YES')} {Translator.translate('prefix_set', ctx, new_prefix=new_prefix)}")

    @configure.group(aliases=["adminroles"], invoke_without_command=True)
    async def admin_roles(self, ctx: commands.Context):
        """configure_admin_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'admin')
        Configuration.validate_config(ctx.guild.id)

    @admin_roles.command(name="add")
    async def add_admin_role(self, ctx, *, role: disnake.Role):
        await add_item(ctx, role, 'admin')

    @admin_roles.command(name="remove")
    async def remove_admin_role(self, ctx, *, role: disnake.Role):
        await remove_item(ctx, role, 'admin')

    @configure.group(aliases=["modroles"], invoke_without_command=True)
    async def mod_roles(self, ctx: commands.Context):
        """configure_mod_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'mod')
        Configuration.validate_config(ctx.guild.id)

    @mod_roles.command(name="add")
    async def add_mod_role(self, ctx, *, role: disnake.Role):
        await add_item(ctx, role, 'mod')

    @mod_roles.command(name="remove")
    async def remove_mod_role(self, ctx, *, role: disnake.Role):
        await remove_item(ctx, role, 'mod')

    @configure.group(aliases=["trustedroles"], invoke_without_command=True)
    async def trusted_roles(self, ctx: commands.Context):
        """configure_trusted_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'trusted')
        Configuration.validate_config(ctx.guild.id)

    @trusted_roles.command(name="add")
    async def add_trusted_role(self, ctx, *, role: disnake.Role):
        await add_item(ctx, role, 'trusted')

    @trusted_roles.command(name="remove")
    async def remove_trusted_role(self, ctx, *, role: disnake.Role):
        await remove_item(ctx, role, 'trusted')

    @configure.command(aliases=["muterole"])
    async def mute_role(self, ctx: commands.Context, role: disnake.Role):
        """configure_mute_help"""
        if role == ctx.guild.default_role:
            return await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'default_role_forbidden', ctx)}")
        if role.tags is not None:
            return await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'tagged_role_forbidden', ctx)}")
        guild: disnake.Guild = ctx.guild
        perms = guild.me.guild_permissions
        if not perms.manage_roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_missing_perm', ctx)}")
            return
        if not guild.me.top_role > role:
            await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate('role_too_high_add', ctx, role=role.name)}")
            return
        Configuration.set_var(ctx.guild.id, "ROLES", "MUTE_ROLE", int(role.id))
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('mute_role_confirmation', ctx, role=role.mention)}")
        failed = []
        for category in guild.categories:
            if category.permissions_for(guild.me).manage_channels:
                try:
                    await category.set_permissions(role, reason=Translator.translate('mute_setup', ctx),
                                                   send_messages=False, add_reactions=False, speak=False, connect=False, send_messages_in_threads=False, create_public_threads=False, create_private_threads=False)
                except disnake.Forbidden:
                    pass

        # sleep a bit so we have time to receive the update events
        await asyncio.sleep(2)

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).manage_channels:
                if channel.overwrites_for(role).is_empty():
                    try:
                        await channel.set_permissions(role, reason=Translator.translate('mute_setup', ctx),
                                                      send_messages=False, add_reactions=False, send_messages_in_threads=False, create_public_threads=False, create_private_threads=False)
                    except disnake.Forbidden:
                        pass
            else:
                failed.append(channel.mention)
        for channel in guild.voice_channels:
            if channel.permissions_for(guild.me).manage_channels:
                if channel.overwrites_for(role).is_empty():
                    try:
                        await channel.set_permissions(role, reason=Translator.translate('mute_setup', ctx), speak=False,
                                                      connect=False)
                    except disnake.Forbidden:
                        pass
            else:
                failed.append(Translator.translate('voice_channel', ctx, channel=channel.name))
        if len(failed) > 0:
            message = f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('mute_setup_failures', ctx, role=role.mention)}\n"
            for fail in failed:
                if len(message) + len(fail) > 2000:
                    await ctx.send(message)
                    message = ""
                message = message + fail
            if len(message) > 0:
                await ctx.send(message)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('mute_setup_complete', ctx)}")

    @configure.group(aliases=["selfrole", "self_role"], invoke_without_command=True)
    async def self_roles(self, ctx: commands.Context):
        """configure_self_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'self', config_section="ROLES")

    @self_roles.command()
    async def add(self, ctx: commands.Context, *, role: disnake.Role):
        await add_item(ctx, role, 'self', config_section="ROLES")
        Selfroles.validate_self_roles(self.bot, ctx.guild)
        self.bot.dispatch("self_roles_update", ctx.guild.id)

    @self_roles.command()
    async def remove(self, ctx: commands.Context, *, role: disnake.Role):
        await remove_item(ctx, role, 'self', config_section="ROLES")
        Selfroles.validate_self_roles(self.bot, ctx.guild)
        self.bot.dispatch("self_roles_update", ctx.guild.id)

    @configure.group(invoke_without_command=True)
    async def allowed_invites(self, ctx: commands.Context):
        """configure_allowed_invite_list_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, "allowed", list_name="invite_list", wrapper="{item}", config_section="CENSORING")

    @allowed_invites.command(name="add")
    async def add_to_allowed_list(self, ctx: commands.Context, server: int):
        await add_item(ctx, ServerHolder(server), "allowed", list_name="invite_list", config_section="CENSORING")

    @allowed_invites.command(name="remove")
    async def remove_from_allowed_list(self, ctx: commands.Context, server: int):
        await remove_item(ctx, ServerHolder(server), "allowed", list_name="invite_list", config_section="CENSORING")

    @configure.command(aliases=["trustedinvitebypass"])
    async def trusted_invite_bypass(self, ctx: commands.Context, enabled_status: bool):
        """censortrustedbypass_help"""
        config_status = await Configuration.get_var(ctx.guild.id, "CENSORING", "ALLOW_TRUSTED_BYPASS")

        enabled_string = "enabled" if enabled_status else "disabled"
        enabled_string = Translator.translate(enabled_string, ctx.guild.id)

        message = MessageUtils.assemble(ctx, "YES", "invite_censor_trusted_bypass", status=enabled_string)

        if enabled_status == config_status:
            message = MessageUtils.assemble(ctx, "NO", f"invite_censor_trusted_bypass_unchanged", status=enabled_string)
        else:
            Configuration.set_var(ctx.guild.id, "CENSORING", "ALLOW_TRUSTED_BYPASS", enabled_status)

        await ctx.send(message)

    @configure.group(aliases=["ignoredUsers"], invoke_without_command=True)
    async def ignored_users(self, ctx):
        """configure_ignored_users_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, "ignored", "users", "<@{item}>", config_section="MESSAGE_LOGS")

    @ignored_users.command(name="add")
    async def addIgnoredUser(self, ctx: commands.Context, user: disnake.Member):
        await add_item(ctx, user, "ignored", "users", config_section="MESSAGE_LOGS")

    @ignored_users.command(name="remove")
    async def removeIgnoredUser(self, ctx: commands.Context, user: disnake.User):
        await remove_item(ctx, user, "ignored", list_name="users", config_section="MESSAGE_LOGS")

    @configure.group("cog_overrides", invoke_without_command=True)
    async def configure_cog_overrides(self, ctx):
        """cog_overrides_help"""
        if ctx.invoked_subcommand is None:
            overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            desc = ""
            for k, v in overrides.items():
                lvl = v["required"]
                if lvl >= 0:
                    desc += f"{k}: {lvl} ({Translator.translate(f'perm_lvl_{lvl}', ctx)})\n"
            if desc == "":
                desc = Translator.translate('no_overrides', ctx)
            embed = disnake.Embed(color=6008770, title=Translator.translate('cog_overrides', ctx), description=desc)
            await ctx.send(embed=embed)

    @configure_cog_overrides.command(name="add")
    async def add_cog_override(self, ctx, cog: str, perm_lvl: int):
        cog = cog
        if cog in ctx.bot.cogs.keys():
            cogo = ctx.bot.cogs[cog]
            if cogo.permissions is None:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('core_cog_no_override', ctx, cog=cog)}")
            elif perm_lvl in range(7):
                min_lvl = cogo.permissions["min"]
                max_lvl = cogo.permissions["max"]
                if perm_lvl < min_lvl:
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_min_perm_violation', ctx, cog=cog, min_lvl=min_lvl, min_lvl_name=Translator.translate(f'perm_lvl_{min_lvl}', ctx))}")
                elif perm_lvl > max_lvl:
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_max_perm_violation', ctx, cog=cog, max_lvl=max_lvl, max_lvl_name=Translator.translate(f'perm_lvl_{max_lvl}', ctx))}")
                else:
                    overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
                    if cog not in overrides:
                        overrides[cog] = {
                            "required": perm_lvl,
                            "commands": {},
                            "people": []
                        }
                    else:
                        overrides[cog]["required"] = perm_lvl
                    Configuration.save(ctx.guild.id)
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('YES')} {Translator.translate('cog_override_applied', ctx, cog=cog, perm_lvl=perm_lvl, perm_lvl_name=Translator.translate(f'perm_lvl_{perm_lvl}', ctx))}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('invalid_override_lvl', ctx)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_not_found', ctx)}")

    @configure_cog_overrides.command(name="remove")
    async def remove_cog_override(self, ctx, cog: str):
        overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
        if cog in overrides:
            overrides[cog]["required"] = -1
            Configuration.save(ctx.guild.id)
            await ctx.send(
                f"{Emoji.get_chat_emoji('YES')} {Translator.translate('cog_override_removed', ctx, cog=cog)}")
        else:
            await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_override_not_found', ctx, cog=cog)}")

    @configure.group(invoke_without_command=True)
    async def command_overrides(self, ctx):
        """command_overrides_help"""
        if ctx.invoked_subcommand is None:
            overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            embed = disnake.Embed(color=6008770, title=Translator.translate('command_overrides', ctx))
            has_overrides = False
            for cog in self.bot.cogs:
                if cog in overrides:
                    out = gen_override_strings(ctx, overrides[cog])
                    if out != "":
                        has_overrides = True
                        embed.add_field(name=cog, value=out)
            if not has_overrides:
                embed.description = Translator.translate('no_overrides', ctx)
            await ctx.send(embed=embed)

    @command_overrides.command(name="set", aliases=["add"])
    async def add_command_override(self, ctx, command: str, perm_lvl: int):
        command = command.lower()
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog = command_object.cog
            cog_name = command_object.cog_name
            if cog.permissions is None:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_core_cog_no_override', ctx, command=command, cog_name=cog_name)}")
            elif perm_lvl in range(7):
                perm_dict = Permissioncheckers.get_perm_dict(command_object.qualified_name.split(" "), cog.permissions)
                if perm_lvl < perm_dict["min"]:
                    lvl = perm_dict["min"]
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_min_perm_violation', ctx, command=command, min_lvl=lvl, min_lvl_name=Translator.translate(f'perm_lvl_{lvl}', ctx))}")
                elif perm_lvl > perm_dict["max"]:
                    lvl = cog.permissions['max']
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_max_perm_violation', ctx, command=command, max_lvl=lvl, max_lvl_name=Translator.translate(f'perm_lvl_{lvl}', ctx))}")
                else:
                    overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
                    if cog_name not in overrides:
                        overrides[cog_name] = {
                            "required": -1,
                            "commands": {},
                            "people": []
                        }
                    override = overrides[cog_name]
                    parts = command_object.qualified_name.split(" ")
                    while len(parts) > 0:
                        part = parts.pop(0)
                        if not part in override["commands"]:
                            override["commands"][part] = override = {
                                "required": -1,
                                "commands": {},
                                "people": []
                            }
                        else:
                            override = override["commands"][part]
                    override["required"] = perm_lvl
                    Configuration.save(ctx.guild.id)
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('YES')} {Translator.translate('command_override_confirmation', ctx, command=command, perm_lvl=perm_lvl, perm_lvl_name=Translator.translate(f'perm_lvl_{perm_lvl}', ctx))}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('invalid_override_lvl', ctx)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_not_found', ctx)}")

    @command_overrides.command(name="remove")
    async def remove_command_override(self, ctx, command: str):
        command = command.lower()
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog_name = command_object.cog_name
            overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            found = False
            if cog_name in overrides:
                override = Permissioncheckers.get_perm_dict(command_object.qualified_name.split(" "),
                                                            overrides[cog_name], True)
                if override is not None:
                    found = True
                    override["required"] = -1
                    Configuration.save(ctx.guild.id)
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('YES')} {Translator.translate('command_override_removed', ctx, command=command)}")
            if not found:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_override_not_found', ctx, command=command)}")

    @configure.command()
    async def perm_denied_message(self, ctx, value: bool):
        """perm_denied_message_help"""
        Configuration.set_var(ctx.guild.id, "GENERAL", "PERM_DENIED_MESSAGE", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('configure_perm_msg_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")

    @configure.command()
    async def language(self, ctx, lang_code: str = None):
        """language_help"""
        if lang_code is None:
            await ctx.send(
                f"See https://crowdin.com/project/gearbot for all available languages and their translation statuses")
        else:
            code = None
            lang_code = lang_code.lower().replace("_", "-")
            for name, lcode in Translator.LANG_CODES.items():
                if lang_code == lcode.lower() or lang_code == name.lower():
                    code = lcode
                    break
            if code is None:
                for name, lcode in Translator.LANG_CODES.items():
                    if lang_code == lcode.lower()[:2]:
                        code = lcode
                        break
            if code is not None:
                Configuration.set_var(ctx.guild.id, "GENERAL", "LANG", code)
                await ctx.send(
                    f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lang_changed', ctx.guild.id, lang=code, lang_name=Translator.LANG_NAMES[code])}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('lang_unknown', ctx.guild.id)}")

    @configure.group(invoke_without_command=True)
    async def lvl4(self, ctx):
        """lvl4_help"""
        pass

    @lvl4.command(name="add")
    async def add_lvl4(self, ctx, command: str, person: disnake.Member):
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog_name = command_object.cog_name
            overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            if cog_name not in overrides:
                overrides[cog_name] = {
                    "required": -1,
                    "commands": {},
                    "people": []
                }
            override = overrides[cog_name]
            parts = command.split(" ")
            while len(parts) > 0:
                part = parts.pop(0)
                if not part in override["commands"]:
                    override["commands"][part] = override = {
                        "required": -1,
                        "commands": {},
                        "people": []
                    }
                else:
                    override = override["commands"][part]
            if person.id not in override["people"]:
                override["people"].append(person.id)
                await ctx.send(
                    f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lvl4_added', ctx, member=person, command=command)}")
            else:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('already_had_lvl4', ctx, member=person, command=command)}")
            Configuration.save(ctx.guild.id)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_not_found', ctx)}")

    @lvl4.command(name="remove")
    async def remove_lvl4(self, ctx, command: str, person: disnake.Member):
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog_name = command_object.cog_name
            overrides = await Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            found = False
            if cog_name in overrides:
                lvl4_list = Permissioncheckers.get_perm_dict(command.split(" "), overrides[cog_name], strict=True)
                if lvl4_list is not None and person.id in lvl4_list["people"]:
                    found = True
            if found:
                lvl4_list["people"].remove(person.id)
                await ctx.send(
                    f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lvl4_removed', ctx, member=person, command=command)}")
                Configuration.save(ctx.guild.id)
            else:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('did_not_have_lvl4', ctx, member=person, command=command)}")

    @configure.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def logging(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = disnake.Embed(color=6008770, title=Translator.translate('log_channels', ctx))
            channels = await Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
            if len(channels) > 0:
                for cid, info in channels.items():
                    embed.add_field(name=cid, value=self.get_channel_properties(ctx, cid, info["CATEGORIES"]))

                await ctx.send(embed=embed)

    @staticmethod
    def get_channel_properties(ctx, cid, info):
        value = ""
        channel = ctx.bot.get_channel(int(cid))
        if channel is None:
            value += f"{Translator.translate('channel_removed', ctx)}\n"
        else:
            value += f"**{Translator.translate('channel', ctx)}**{channel.mention}\n\n"
            perms = ["send_messages", "embed_links", "attach_files"]
            permissions = channel.permissions_for(channel.guild.me)
            missing = [p for p in perms if not getattr(permissions, p)]
            value += f"**{Translator.translate('channel_perms', ctx)}** \n"
            if len(missing) == 0:
                value += f"{Emoji.get_chat_emoji('YES')} {Translator.translate('full_channel_perms', ctx)}\n\n"
            else:
                value += f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('missing_channel_perms', ctx, perms=', '.join(missing))}\n\n"
        value += f"**{Translator.translate('to_be_logged', ctx)}** \n{', '.join(info)}\n\n"
        return value

    @logging.command(name="add")
    async def add_logging(self, ctx, channel: disnake.TextChannel, *, types):
        cid = str(channel.id)
        channels = await Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
        if cid not in channels:
            channels[cid] = {
                "CATEGORIES": [],
                "DISABLED_KEYS": []
            }
        info = channels[cid]["CATEGORIES"]
        added = []
        ignored = []
        message = ""
        known, unknown = self.extract_types(types)
        for t in known:
            if t in info:
                ignored.append(t)
            else:
                info.append(t)
                added.append(t)
        if len(added) > 0:
            message += f"{Emoji.get_chat_emoji('YES')} {Translator.translate('logs_added', ctx)}{', '.join(added)}"

        if len(ignored) > 0:
            message += f"\n{Emoji.get_chat_emoji('WARNING')}{Translator.translate('logs_ignored', ctx)}{', '.join(ignored)}"

        if len(unknown) > 0:
            message += f"\n {Emoji.get_chat_emoji('NO')}{Translator.translate('logs_unknown', ctx)}{', '.join(unknown)}"

        embed = disnake.Embed(color=6008770)
        embed.add_field(name=channel.id,
                        value=self.get_channel_properties(ctx, channel.id, channels[cid]["CATEGORIES"]))
        await ctx.send(message, embed=embed)
        Configuration.save(ctx.guild.id)

        features = []
        for a in added:
            feature = Utils.find_key(Features.requires_logging, a)
            if feature is not None and not await Configuration.get_var(ctx.guild.id, feature):
                features.append(feature)

        if len(features) > 0:
            message = None

            async def yes(interaction: disnake.Interaction):
                await self._enable_feature(ctx, ", ".join(features), interaction)
                await interaction.response.edit_message(content="Features enabled", view=None)

            async def no(interaction):
                await interaction.response.edit_message(content=MessageUtils.assemble(ctx, 'NO', 'command_canceled'),
                                                        view=None)

            async def timeout():
                if message is not None:
                    await message.edit(content=MessageUtils.assemble(ctx, 'NO', 'command_canceled'), view=None)

            def check(interaction: Interaction):
                return ctx.author.id == interaction.user.id and interaction.message.id == message.id

            message = await ctx.send(Translator.translate('confirmation_enable_features', ctx.guild.id, count=len(features)) + f"\n{', '.join(features)}",
                                     view=Confirm(ctx.guild.id, on_yes=yes, on_no=no, on_timeout=timeout, check=check, timeout=60))

    @logging.command(name="remove")
    async def remove_logging(self, ctx, cid: LoggingChannel, *, types):
        channel = self.bot.get_channel(int(cid))
        channels = await Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
        if cid not in channels:
            await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate('no_log_channel', ctx, channel=f'<{cid}>')}")
        else:
            info = channels[cid]["CATEGORIES"]
            removed = []
            ignored = []
            unable = []
            known, unknown = self.extract_types(types)
            message = ""
            for t in known:
                if t in info:
                    removed.append(t)
                    info.remove(t)
                else:
                    ignored.append(t)
            if len(removed) > 0:
                message += f"{Emoji.get_chat_emoji('YES')} {Translator.translate('logs_disabled_channel', ctx, channel=channel.mention if channel is not None else cid)}{', '.join(removed)}"

            if len(ignored) > 0:
                message += f"\n{Emoji.get_chat_emoji('WARNING')}{Translator.translate('logs_already_disabled_channel', ctx, channel=channel.mention if channel is not None else cid)}{', '.join(ignored)}"

            if len(unable) > 0:
                message += f"\n {Emoji.get_chat_emoji('NO')}{Translator.translate('logs_unable', ctx)} {', '.join(unable)}"

            if len(unknown) > 0:
                message += f"\n {Emoji.get_chat_emoji('NO')}{Translator.translate('logs_unknown', ctx)}{', '.join(unknown)}"

            if len(info) > 0:
                embed = disnake.Embed(color=6008770)
                embed.add_field(name=cid, value=self.get_channel_properties(ctx, cid, channels[cid]["CATEGORIES"]))
            else:
                embed = None
            await ctx.send(message, embed=embed)
            empty = []
            for cid, info in channels.items():
                if len(info) == 0:
                    empty.append(cid)
            for e in empty:
                del channels[e]
            Configuration.save(ctx.guild.id)

    @logging.command()
    async def dash(self, ctx):
        await ctx.send(embed=self.get_logging_status(ctx))

    def get_logging_status(self, ctx):
        enabled = f"{Emoji.get_chat_emoji('YES')} {Translator.translate('enabled', ctx)}"
        disabled = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('disabled', ctx)}"
        embed = disnake.Embed(color=6008770, title=Translator.translate('log_types', ctx))
        for t in self.LOGGING_TYPES:
            e = Features.is_logged(ctx.guild.id, t)
            embed.add_field(name=t, value=enabled if e else disabled)
        return embed

    @configure.group(invoke_without_command=True)
    @commands.guild_only()
    async def features(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=await self.get_features_status(ctx))

    @features.command(name="enable")
    async def enable_feature(self, ctx, types):
        await self._enable_feature(ctx, types, None)

    async def _enable_feature(self, ctx, types, interaction):
        types = types.upper()
        enabled = []
        ignored = []
        known = []
        unknown = []
        for t2 in types.split(","):
            for t in t2.split():
                t = t.strip(",").strip()
                if t != "":
                    if t in Features.requires_logging:
                        known.append(t)
                    else:
                        unknown.append(t)
        message = ""
        for t in known:
            if await Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED"):
                ignored.append(t)
            else:
                enabled.append(t)
                Configuration.set_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED",
                                      True)
                if t == "EDIT_LOGS":
                    if interaction is None:
                        await ctx.send(Translator.translate('minor_log_caching_start', ctx))
                    # self.bot.to_cache.append(ctx)

        if len(enabled) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'YES', 'features_enabled', count=len(enabled)) + ', '.join(
                enabled)

        if len(ignored) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'WARNING', 'feature_already_enabled',
                                             count=len(ignored)) + ', '.join(ignored)

        if len(unknown) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'NO', 'logs_unknown', count=len(unknown)) + ', '.join(
                unknown)

        if interaction is None:
            await ctx.send(message, embed=await self.get_features_status(ctx))
        else:
            interaction.response.edit_message(content=message, embed=await self.get_features_status(ctx), view=None)

    @staticmethod
    async def get_features_status(ctx):
        enabled = f"{Emoji.get_chat_emoji('YES')} {Translator.translate('enabled', ctx)}"
        disabled = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('disabled', ctx)}"
        embed = disnake.Embed(color=6008770, title=Translator.translate('features', ctx))
        for f, t in Features.requires_logging.items():
            e = await Configuration.get_var(ctx.guild.id, t, "ENABLED", f)
            embed.add_field(name=f, value=enabled if e else disabled)
        return embed

    def can_remove(self, guild, logging):
        counts = dict()
        for cid, info in Configuration.legacy_get_var(guild, "LOG_CHANNELS").items():
            for i in info:
                if i not in counts:
                    counts[i] = 1
                else:
                    counts[i] += 1
        return logging not in Features.requires_logging.values() or (
                logging in counts and counts[logging] > 1) or Configuration.legacy_get_var(
            "MESSAGE_LOGS" if logging == "EDIT_LOGS" else "CENSORING", "ENABLED", False)

    @features.command(name="disable")
    async def feature_disable(self, ctx, types: str):
        types = types.upper()
        disabled = []
        ignored = []
        known = []
        unknown = []
        for t2 in types.split(","):
            for t in t2.split():
                t = t.strip(",").strip()
                if t != "":
                    if t in Features.requires_logging:
                        known.append(t)
                    else:
                        unknown.append(t)
        message = ""
        for t in known:
            if not await Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED"):
                ignored.append(t)
            else:
                disabled.append(t)
                Configuration.set_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED",
                                      False)

        if len(disabled) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'YES', 'features_disabled', count=len(disabled)) + ', '.join(
                disabled)

        if len(ignored) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'WARNING', 'feature_already_disabled',
                                             count=len(ignored)) + ', '.join(ignored)

        if len(unknown) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'NO', 'features_unknown', count=len(unknown)) + ', '.join(
                unknown)

        await ctx.send(message, embed=await self.get_features_status(ctx))

    def extract_types(self, raw_types):
        raw_types = raw_types.upper()
        if "EVERYTHING" in raw_types:
            return self.LOGGING_TYPES, []
        types = []
        unknown = []
        for t2 in raw_types.split(","):
            for t in t2.split():
                t = t.strip(",").strip()
                if t != "":
                    if t in self.LOGGING_TYPES:
                        types.append(t)
                    else:
                        unknown.append(t)
        return types, unknown

    @configure.group(invoke_without_command=True)
    @commands.guild_only()
    async def ignored_channels(self, ctx):
        """ignored_channels_help"""
        if ctx.invoked_subcommand == self.ignored_channels:
            await ctx.invoke(self.bot.get_command("help"), query="configure ignored_channels")

    @ignored_channels.group("changes", invoke_without_command=True)
    @commands.guild_only()
    async def ignored_channels_changes(self, ctx):
        """ignored_channels_changes_help"""
        if ctx.invoked_subcommand == self.ignored_channels_changes:
            await ctx.invoke(self.bot.get_command("help"), query="configure ignored_channels changes")

    @ignored_channels_changes.command("add")
    async def ignored_channels_changes_add(self, ctx, channel: typing.Union[disnake.TextChannel, disnake.VoiceChannel]):
        """ignored_channels_add_help"""
        channels = await Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_CHANGES')
        if channel.id in channels:
            await MessageUtils.send_to(ctx, 'NO', 'ignored_channels_already_on_list', channel=channel.mention)
        else:
            channels.append(channel.id)
            await MessageUtils.send_to(ctx, 'YES', 'ignored_channels_changes_added', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @ignored_channels_changes.command("remove")
    async def ignored_channels_changes_remove(self, ctx, channel: typing.Union[disnake.TextChannel, disnake.VoiceChannel]):
        """ignored_channels_remove_help"""
        channels = await Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_CHANGES')
        if not channel.id in channels:
            await MessageUtils.send_to(ctx, 'NO', 'ignored_channels_not_on_list', channel=channel.mention)
        else:
            channels.remove(channel.id)
            await MessageUtils.send_to(ctx, 'YES', 'ignored_channels_changes_removed', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @ignored_channels_changes.command("list")
    async def ignored_channels_changes_list(self, ctx):
        """ignored_channels_list_help"""
        await self.list_channels(ctx, "changes")

    @staticmethod
    async def list_channels(ctx, type):
        channel_list = await Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", f'IGNORED_CHANNELS_{type.upper()}')
        if len(channel_list) > 0:
            channels = "\n".join(ctx.guild.get_channel(c).mention for c in channel_list)
        else:
            channels = Translator.translate('no_ignored_channels', ctx)
        embed = disnake.Embed(color=ctx.guild.roles[-1].color, description=channels)
        embed.set_author(name=Translator.translate(f'ignored_channels_list_{type}', ctx, guild=ctx.guild.name),
                         icon_url=ctx.guild.icon.url)
        await ctx.send(embed=embed)

    @ignored_channels.group("edits", aliases=["edit"], invoke_without_command=True)
    @commands.guild_only()
    async def ignored_channels_edits(self, ctx):
        """ignored_channels_edits_help"""
        if ctx.invoked_subcommand == self.ignored_channels_edits:
            await ctx.invoke(self.bot.get_command("help"), query="configure ignored_channels other")

    @ignored_channels_edits.command("add")
    async def ignored_channels_edits_add(self, ctx, channel: typing.Union[disnake.TextChannel, disnake.VoiceChannel]):
        """ignored_channels_add_help"""
        channels = await Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_OTHER')
        if channel.id in channels:
            await MessageUtils.send_to(ctx, 'NO', 'ignored_channels_already_on_list', channel=channel.mention)
        else:
            channels.append(channel.id)
            await MessageUtils.send_to(ctx, 'YES', 'ignored_channels_edits_added', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @ignored_channels_edits.command("remove")
    async def ignored_channels_edits_remove(self, ctx, channel: typing.Union[disnake.TextChannel, disnake.VoiceChannel]):
        """ignored_channels_remove_help"""
        channels = await Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_OTHER')
        if channel.id not in channels:
            await MessageUtils.send_to(ctx, 'NO', 'ignored_channels_not_on_list')
        else:
            channels.remove(channel.id)
            await MessageUtils.send_to(ctx, 'YES', 'ignored_channels_edits_removed', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @ignored_channels_edits.command("list")
    async def ignored_channels_edits_list(self, ctx):
        """ignored_channels_list_help"""
        await self.list_channels(ctx, "other")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def disable(self, ctx: commands.Context):
        """disable_help"""
        pass

    @disable.command()
    async def mute(self, ctx: commands.Context):
        """disable_mute_help"""
        await Infraction.filter(type="Mute", guild_id=ctx.guild.id, active=True).update(active=False)
        infractions = await Infraction.filter(type="Mute", guild_id=ctx.guild.id, active=True)
        role = ctx.guild.get_role(await Configuration.get_var(ctx.guild.id, "ROLES", "MUTE_ROLE"))
        for i in infractions:
            member = ctx.guild.get_member(i.user_id)
            if member is not None:
                await member.remove_roles(role, reason=f"Mute feature has been disabled")
        Configuration.set_var(ctx.guild.id, "ROLES", "MUTE_ROLE", 0)
        await ctx.send(
            "Mute feature has been disabled, all people muted have been unmuted and the role can now be removed.")

    async def dm_configure(self, ctx, kind, value):
        config_key = f"DM_ON_{kind.upper()}"
        current = await Configuration.get_var(ctx.guild.id, "INFRACTIONS", config_key)
        if value is None:
            await MessageUtils.send_to(ctx, 'WRENCH', f'dm_on_{kind}_msg_is_' + ('enabled' if current else 'disabled'))
        elif current != value:
            Configuration.set_var(ctx.guild.id, "INFRACTIONS", config_key, value)
            await MessageUtils.send_to(ctx, 'YES', f'dm_on_{kind}_msg_' + ('enabled' if value else 'disabled'))
        else:
            await MessageUtils.send_to(ctx, 'WARNING',
                                       f'dm_on_{kind}_msg_already_' + ('enabled' if value else 'disabled'))

    @configure.command()
    async def dm_on_warn(self, ctx, value: bool = None):
        """dm_on_warn_help"""
        await self.dm_configure(ctx, 'warn', value)

    @configure.command()
    async def dm_on_kick(self, ctx, value: bool = None):
        """dm_on_kick_help"""
        await self.dm_configure(ctx, 'kick', value)

    @configure.command()
    async def dm_on_ban(self, ctx, value: bool = None):
        """dm_on_ban_help"""
        await self.dm_configure(ctx, 'ban', value)

    @configure.command()
    async def dm_on_tempban(self, ctx, value: bool = None):
        """dm_on_tempban_help"""
        await self.dm_configure(ctx, 'tempban', value)

    @configure.command()
    async def dm_on_mute(self, ctx, value: bool = None):
        """dm_on_mute_help"""
        await self.dm_configure(ctx, 'mute', value)

    @configure.command()
    async def dm_on_unmute(self, ctx, value: bool = None):
        """dm_on_unmute_help"""
        await self.dm_configure(ctx, 'unmute', value)

    @configure.command(aliases=["dm_on"])
    async def dm_notifications(self, ctx):
        """dm_notifications_help"""
        embed = disnake.Embed(color=600870, title=Translator.translate('infraction_dm_settings', ctx))
        enabled = f"{Emoji.get_chat_emoji('YES')} {Translator.translate('enabled', ctx)}"
        disabled = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('disabled', ctx)}"

        for x in ["WARN", "UNMUTE", "MUTE", "KICK", "BAN", "TEMPBAN"]:
                key = f"DM_ON_{x}"
                v = await Configuration.get_var(ctx.guild.id, "INFRACTIONS", key)
                embed.add_field(name=key, value=enabled if v else disabled)
        
        await ctx.send(embed=embed)

    @configure.command()
    async def log_embeds(self, ctx, value: bool):
        Configuration.set_var(ctx.guild.id, "MESSAGE_LOGS", "EMBED", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('embed_log_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")

    @configure.command(aliases=["log_message_id"])
    async def log_message_ids(self, ctx, value: bool):
        Configuration.set_var(ctx.guild.id, "MESSAGE_LOGS", "MESSAGE_ID", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('message_id_log_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")

    @configure.group(aliases=["censorlist", "cl"], invoke_without_command=True)
    async def censor_list(self, ctx):
        """censor_list_help"""
        if ctx.invoked_subcommand is None:
            censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "TOKEN_CENSORLIST")
            if len(censor_list) > 0:
                pages = Pages.paginate("\n".join(censor_list))
            else:
                pages = [Translator.translate('censor_list_empty', ctx)]
            content, view, page_num = SimplePager.get_parts(pages, 0, ctx.guild.id, 'censor_list')
            await ctx.send(f"**{Translator.translate(f'censor_list', ctx, server=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{pages[0]}```", view=view)

    @censor_list.command("add")
    async def censor_list_add(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "TOKEN_CENSORLIST")
        if word in censor_list:
            await MessageUtils.send_to(ctx, "NO", "already_censored", word=word)
        else:
            censor_list.append(word)
            await MessageUtils.send_to(ctx, "YES", "entry_added", entry=word)
            Configuration.save(ctx.guild.id)

    @censor_list.command("remove")
    async def censor_list_remove(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "TOKEN_CENSORLIST")
        if word not in censor_list:
            await MessageUtils.send_to(ctx, "NO", "not_censored", word=word)
        else:
            censor_list.remove(word)
            await MessageUtils.send_to(ctx, "YES", "entry_removed", entry=word)
            Configuration.save(ctx.guild.id)

    @censor_list.command("get")
    async def censor_list_get(self, ctx):
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "TOKEN_CENSORLIST")
        if len(censor_list) > 0:
            out = '\n'.join(censor_list)
            buffer = io.BytesIO()
            buffer.write(out.encode())
            buffer.seek(0)
            await MessageUtils.send_to(ctx, 'YES', 'censor_list_file',
                                       attachment=disnake.File(buffer, filename="token_censorlist.txt"),
                                       server=ctx.guild.name)
        else:
            await MessageUtils.send_to(ctx, 'WARNING', 'word_censor_list_empty')

    @censor_list.command("upload")
    async def censor_list_upload(self, ctx):
        await self.receive_list(ctx, "CENSORING", "TOKEN_CENSORLIST", "censor")

    async def receive_list(self, ctx, target_cat, target_key, prefix):
        if len(ctx.message.attachments) != 1:
            await MessageUtils.send_to(ctx, 'NO', 'censor_attachment_required')
            return
        else:
            attachment = ctx.message.attachments[0]
            if not attachment.filename.endswith(".txt"):
                await MessageUtils.send_to(ctx, 'NO', 'censor_attachment_required')
                return
            elif attachment.size > 1_000_000:
                await MessageUtils.send_to(ctx, 'NO', 'attachment_too_big')
                return

            b = await attachment.read()

            try:
                content = b.decode('utf-8').lower()
            except Exception:
                await MessageUtils.send_to(ctx, 'NO', 'list_parsing_failed')
                return

            max_length = await Configuration.get_var(ctx.guild.id, target_cat, "MAX_LIST_LENGTH")

            new_list = content.splitlines()
            if len(new_list) > max_length:
                await MessageUtils.send_to(ctx, 'NO', 'list_too_long', length=max_length)
                return

            Configuration.set_var(ctx.guild.id, target_cat, target_key, new_list)
            if ctx.guild.id in self.bot.get_cog("Censor").regexes:
                del self.bot.get_cog("Censor").regexes[ctx.guild.id]

            await MessageUtils.send_to(ctx, 'YES', f'{prefix}_list_set')

    @configure.group(aliases=["wordcensorlist", "wcl"], invoke_without_command=True)
    async def word_censor_list(self, ctx):
        if ctx.invoked_subcommand is None:
            censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "WORD_CENSORLIST")
            if len(censor_list) > 0:
                pages = Pages.paginate("\n".join(censor_list))
            else:
                pages = [Translator.translate('word_censor_list_empty', ctx)]
            content, view, page_num = SimplePager.get_parts(pages, 0, ctx.guild.id, 'word_censor_list')
            await ctx.send(
                f"**{Translator.translate(f'word_censor_list', ctx, server=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{pages[0]}```",
                view=view)

    @word_censor_list.command("add")
    async def word_censor_list_add(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "WORD_CENSORLIST")
        if word in censor_list:
            await MessageUtils.send_to(ctx, "NO", "word_already_censored", word=word)
        else:
            censor_list.append(word)
            await MessageUtils.send_to(ctx, "YES", "word_entry_added", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Censor").regexes:
                del self.bot.get_cog("Censor").regexes[ctx.guild.id]

    @word_censor_list.command("remove")
    async def word_censor_list_remove(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "WORD_CENSORLIST")
        if word not in censor_list:
            await MessageUtils.send_to(ctx, "NO", "word_not_censored", word=word)
        else:
            censor_list.remove(word)
            await MessageUtils.send_to(ctx, "YES", "word_entry_removed", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Censor").regexes:
                del self.bot.get_cog("Censor").regexes[ctx.guild.id]

    @word_censor_list.command("get")
    async def word_censor_list_get(self, ctx):
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "WORD_CENSORLIST")
        if len(censor_list) > 0:
            out = '\n'.join(censor_list)
            buffer = io.BytesIO()
            buffer.write(out.encode())
            buffer.seek(0)
            await MessageUtils.send_to(ctx, 'YES', 'word_censor_list_file',
                                       attachment=disnake.File(buffer, filename="word_censorlist.txt"),
                                       server=ctx.guild.name)
        else:
            await MessageUtils.send_to(ctx, 'WARNING', 'word_censor_list_empty')

    @word_censor_list.command("upload")
    async def word_censor_list_upload(self, ctx):
        await self.receive_list(ctx, "CENSORING", "WORD_CENSORLIST", "word_censor")

    @configure.group(aliases=["flaglist", "fl"], invoke_without_command=True)
    async def flag_list(self, ctx):
        """flag_list_help"""
        if ctx.invoked_subcommand is None:
            censor_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "TOKEN_LIST")
            if len(censor_list) > 0:
                pages = Pages.paginate("\n".join(censor_list))
            else:
                pages = [Translator.translate('flag_list_empty', ctx)]
            content, view, page_num = SimplePager.get_parts(pages, 0, ctx.guild.id, 'flag_list')
            await ctx.send(
                f"**{Translator.translate(f'flagged_list', ctx, server=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{pages[0]}```",
                view=view)

    @flag_list.command("add")
    async def flag_list_add(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "TOKEN_LIST")
        if word in censor_list:
            await MessageUtils.send_to(ctx, "NO", "already_flagged", word=word)
        else:
            censor_list.append(word)
            await MessageUtils.send_to(ctx, "YES", "flag_added", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Moderation").regexes:
                del self.bot.get_cog("Moderation").regexes[ctx.guild.id]

    @flag_list.command("remove")
    async def flag_list_remove(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "TOKEN_LIST")
        if word not in censor_list:
            await MessageUtils.send_to(ctx, "NO", "not_flagged", word=word)
        else:
            censor_list.remove(word)
            await MessageUtils.send_to(ctx, "YES", "flag_removed", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Moderation").regexes:
                del self.bot.get_cog("Moderation").regexes[ctx.guild.id]

    @flag_list.command("upload")
    async def flag_list_upload(self, ctx):
        await self.receive_list(ctx, "FLAGGING", "TOKEN_LIST", "flag")

    @flag_list.command("get")
    async def flag_list_get(self, ctx):
        flag_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "TOKEN_LIST")
        if len(flag_list) > 0:
            out = '\n'.join(flag_list)
            buffer = io.BytesIO()
            buffer.write(out.encode())
            buffer.seek(0)
            await MessageUtils.send_to(ctx, 'YES', 'flag_list_file',
                                       attachment=disnake.File(buffer, filename="flag_list.txt"),
                                       server=ctx.guild.name)
        else:
            await MessageUtils.send_to(ctx, 'WARNING', 'flag_list_empty')

    @configure.group(aliases=["wordflaglist", "wfl"], invoke_without_command=True)
    async def word_flag_list(self, ctx):
        """word_flag_list_help"""
        if ctx.invoked_subcommand is None:
            censor_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "WORD_LIST")
            if len(censor_list) > 0:
                pages = Pages.paginate("\n".join(censor_list))
            else:
                pages = [Translator.translate('word_flag_list_empty', ctx)]
            content, view, page_num = SimplePager.get_parts(pages, 0, ctx.guild.id, 'word_flag_list')
            await ctx.send(
                f"**{Translator.translate(f'flagged_word_list', ctx, server=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{pages[0]}```",
                view=view)

    @word_flag_list.command("add")
    async def word_flag_list_add(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "WORD_LIST")
        if word in censor_list:
            await MessageUtils.send_to(ctx, "NO", "word_already_flagged", word=word)
        else:
            censor_list.append(word)
            await MessageUtils.send_to(ctx, "YES", "word_flag_added", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Moderation").regexes:
                del self.bot.get_cog("Moderation").regexes[ctx.guild.id]

    @word_flag_list.command("remove")
    async def word_flag_list_remove(self, ctx, *, word: str):
        word = word.lower()
        censor_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "WORD_LIST")
        if word not in censor_list:
            await MessageUtils.send_to(ctx, "NO", "word_not_flagged", word=word)
        else:
            censor_list.remove(word)
            await MessageUtils.send_to(ctx, "YES", "word_flag_removed", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Moderation").regexes:
                del self.bot.get_cog("Moderation").regexes[ctx.guild.id]

    @word_flag_list.command("upload")
    async def word_flag_list_upload(self, ctx):
        await self.receive_list(ctx, "FLAGGING", "WORD_LIST", "word_flag")

    @word_flag_list.command("get")
    async def word_flag_list_get(self, ctx):
        flag_list = await Configuration.get_var(ctx.guild.id, "FLAGGING", "WORD_LIST")
        if len(flag_list) > 0:
            out = '\n'.join(flag_list)
            buffer = io.BytesIO()
            buffer.write(out.encode())
            buffer.seek(0)
            await MessageUtils.send_to(ctx, 'YES', 'word_flag_list_file',
                                       attachment=disnake.File(buffer, filename="word_flag_list.txt"),
                                       server=ctx.guild.name)
        else:
            await MessageUtils.send_to(ctx, 'WARNING', 'word_flag_list_empty')

    @configure.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def role_list(self, ctx):
        """configure_role_list_help"""
        if ctx.invoked_subcommand is None:
            items = await Configuration.get_var(ctx.guild.id, "ROLES", f"ROLE_LIST")
            mode = "allow" if await Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE") else "block"
            if len(items) == 0:
                desc = Translator.translate(f"no_role_{mode}", ctx)
            else:
                desc = "\n".join(f"<@&{item}>" for item in items)
            embed = disnake.Embed(title=Translator.translate(f"current_role_{mode}_list", ctx), description=desc)
            await ctx.send(embed=embed)

    @role_list.command("add")
    async def role_list_add(self, ctx, *, role: disnake.Role):
        """configure_role_list_add"""
        roles = await Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST")
        mode = "allow" if await Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE") else "block"
        if role == ctx.guild.default_role:
            await MessageUtils.send_to(ctx, "NO", "default_role_forbidden")
        elif role.id in roles:
            await MessageUtils.send_to(ctx, "NO", f"role_list_add_fail", role=Utils.escape_markdown(role.name))
        else:
            roles.append(role.id)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"role_list_add_confirmation_{mode}",
                                       role=Utils.escape_markdown(role.name))

    @role_list.command("remove", aliases=["rmv"])
    async def role_list_remove(self, ctx, *, role: disnake.Role):
        """configure_role_list_remove"""
        roles = await Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST")
        mode = "allow" if await Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE") else "block"
        if role.id not in roles:
            await MessageUtils.send_to(ctx, "NO", f"role_list_rmv_fail_{mode}", role=Utils.escape_markdown(role.name))
        else:
            roles.remove(role.id)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"role_list_rmv_confirmation_{mode}",
                                       role=Utils.escape_markdown(role.name))

    @role_list.command("mode")
    async def role_list_mode(self, ctx, mode: ListMode):
        """configure_role_list_mode"""
        Configuration.set_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE", mode)
        mode = "allowed" if mode else "blocked"
        await MessageUtils.send_to(ctx, "YES", f"role_list_mode_{mode}")

    @configure.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def domain_list(self, ctx):
        """configure_domain_list_help"""
        if ctx.invoked_subcommand is None:
            items = await Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST")
            mode = "allowed" if await Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED") else "blocked"
            if len(items) == 0:
                desc = Translator.translate(f"empty_domain_list", ctx)
            else:
                desc = "\n".join(f"{item}" for item in items)
            embed = disnake.Embed(title=Translator.translate(f"current_domain_list_{mode}", ctx), description=desc)
            await ctx.send(embed=embed)

    @domain_list.command("add")
    async def domain_list_add(self, ctx, *, domain):
        """configure_domain_list_add"""
        domain = domain.lower()
        domains = await Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST")
        mode = "allow" if await Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED") else "block"
        if domain in domains:
            await MessageUtils.send_to(ctx, "NO", f"domain_list_add_fail_{mode}", domain=domain)
        else:
            domains.append(domain)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"domain_list_add_confirmation_{mode}", domain=domain)

    @domain_list.command("remove", aliases=["rmv"])
    async def domain_list_remove(self, ctx, *, domain):
        """configure_domain_list_remove"""
        domains = await Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST")
        mode = "allow" if await Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED") else "block"
        if domain not in domains:
            await MessageUtils.send_to(ctx, "NO", f"domain_list_rmv_fail_{mode}", domain=domain)
        else:
            domains.remove(domain)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"domain_list_rmv_confirmation_{mode}", domain=domain)

    @domain_list.command("mode")
    async def domain_list_mode(self, ctx, mode: ListMode):
        """configure_domain_list_mode"""
        Configuration.set_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED", mode)
        mode = "allow" if mode else "block"
        await MessageUtils.send_to(ctx, "YES", f"domain_list_mode_{mode}")

    @domain_list.command("get")
    async def domain_list_get(self, ctx):
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST")
        if len(censor_list) > 0:
            out = '\n'.join(censor_list)
            buffer = io.BytesIO()
            buffer.write(out.encode())
            buffer.seek(0)
            await MessageUtils.send_to(ctx, 'YES', 'domain_censor_list_file',
                                       attachment=disnake.File(buffer, filename="domain_list.txt"),
                                       server=ctx.guild.name)
        else:
            await MessageUtils.send_to(ctx, 'WARNING', 'domain_list_empty')

    @domain_list.command("upload")
    async def domain_list_upload(self, ctx):
        await self.receive_list(ctx, "CENSORING", "DOMAIN_LIST", "domain")

    @configure.command()
    @commands.guild_only()
    async def timezone(self, ctx, new_zone=None):
        """timezone_help"""
        current_zone = await Configuration.get_var(ctx.guild.id, "GENERAL", "TIMEZONE")
        if new_zone is None:
            # no new zone, spit out the current one
            await MessageUtils.send_to(ctx, "CLOCK", "current_timezone", timezone=current_zone)
        else:
            try:
                zone = str(pytz.timezone(new_zone))
            except UnknownTimeZoneError:
                await MessageUtils.send_to(ctx, "NO", "invalid_timezone")
            else:
                if current_zone == new_zone:
                    await MessageUtils.send_to(ctx, "WHAT", "same_timezone", timezone=current_zone)
                else:
                    Configuration.set_var(ctx.guild.id, "GENERAL", "TIMEZONE", zone)
                    await MessageUtils.send_to(ctx, "YES", "timezone_set", timezone=zone)

    @configure.group(invoke_without_command=True)
    async def full_message_censor_list(self, ctx):
        """full_message_censor_list_help"""
        if ctx.invoked_subcommand is None:
            censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "FULL_MESSAGE_LIST")
            if len(censor_list) > 0:
                pages = Pages.paginate("\n".join(censor_list))
            else:
                pages = [Translator.translate('full_censor_list_empty', ctx)]
            content, view, page_num = SimplePager.get_parts(pages, 0, ctx.guild.id, 'full_censor_list')
            await ctx.send(
                f"**{Translator.translate(f'full_message_censor_list', ctx, server=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{pages[0]}```",
                view=view)

    @full_message_censor_list.command("add")
    async def full_message_censor_list_add(self, ctx, *, message: str):
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "FULL_MESSAGE_LIST")
        if message.lower() in censor_list:
            await MessageUtils.send_to(ctx, "NO", "already_censored", word=message)
        else:
            censor_list.append(message.lower())
            await MessageUtils.send_to(ctx, "YES", "entry_added", entry=message)
            Configuration.save(ctx.guild.id)

    @full_message_censor_list.command("remove")
    async def full_message_censor_list_remove(self, ctx, *, message: str):
        censor_list = await Configuration.get_var(ctx.guild.id, "CENSORING", "FULL_MESSAGE_LIST")
        if message.lower() not in censor_list:
            await MessageUtils.send_to(ctx, "NO", "not_censored", word=message)
        else:
            censor_list.remove(message.lower())
            await MessageUtils.send_to(ctx, "YES", "entry_removed", entry=message)
            Configuration.save(ctx.guild.id)

    @configure.command()
    async def censor_emoji_only_messages(self, ctx, value: bool):
        "censor_emoji_only_messages_help"
        Configuration.set_var(ctx.guild.id, "CENSORING", "CENSOR_EMOJI_ONLY_MESSAGES", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('censor_emoji_messages_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")

    @configure.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def custom_commands_role_list(self, ctx):
        if ctx.invoked_subcommand is None:
            items = await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", f"ROLES")
            mode = "allow" if await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "ROLE_REQUIRED") else "block"
            if len(items) == 0:
                desc = Translator.translate(f"custom_commands_role_list_empty_{mode}", ctx)
            else:
                desc = "\n".join(f"<@&{item}>" for item in items)
            embed = disnake.Embed(title=Translator.translate(f"custom_commands_current_role_{mode}_list", ctx),
                                  description=desc)
            await ctx.send(embed=embed)

    @custom_commands_role_list.command("add")
    async def custom_commands_role_list_add(self, ctx, *, role: disnake.Role):
        roles = await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "ROLES")
        mode = "allow" if await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "ROLE_REQUIRED") else "block"
        if role == ctx.guild.default_role:
            await MessageUtils.send_to(ctx, "NO", "default_role_forbidden")
        elif role.id in roles:
            await MessageUtils.send_to(ctx, "NO", f"custom_commands_role_list_add_fail",
                                       role=Utils.escape_markdown(role.name))
        else:
            roles.append(role.id)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"custom_commands_role_list_add_confirmation_{mode}",
                                       role=Utils.escape_markdown(role.name))

    @custom_commands_role_list.command("remove", aliases=["rmv"])
    async def custom_commands_role_list_remove(self, ctx, *, role: disnake.Role):
        roles = await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "ROLES")
        mode = "allow" if await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "ROLE_REQUIRED") else "block"
        if role.id not in roles:
            await MessageUtils.send_to(ctx, "NO", f"custom_commands_role_list_rmv_fail_{mode}",
                                       role=Utils.escape_markdown(role.name))
        else:
            roles.remove(role.id)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"custom_commands_role_list_rmv_confirmation_{mode}",
                                       role=Utils.escape_markdown(role.name))

    @commands.guild_only()
    @configure.group(invoke_without_command=True)
    @commands.bot_has_permissions(embed_links=True)
    async def custom_commands_channel_list(self, ctx):
        if ctx.invoked_subcommand is None:
            items = await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "CHANNELS")
            mode = "use" if await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "CHANNELS_IGNORED") else "ignore"
            if len(items) == 0:
                desc = Translator.translate(f"custom_commands_channel_list_empty_{mode}", ctx)
            else:
                desc = "\n".join(f"<#{item}>" for item in items)
            embed = disnake.Embed(title=Translator.translate(f"custom_commands_current_channel_{mode}_list", ctx),
                                  description=desc)
            await ctx.send(embed=embed)

    @custom_commands_channel_list.command("add")
    async def custom_commands_ignored_channels_add(self, ctx, channel: TextChannel):
        channels = await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", 'CHANNELS')
        mode = "use" if await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "CHANNELS_IGNORED") else "ignore"
        if channel.id in channels:
            await MessageUtils.send_to(ctx, 'NO', f'custom_commands_channel_already_on_{mode}_list',
                                       channel=channel.mention)
        else:
            channels.append(channel.id)
            await MessageUtils.send_to(ctx, 'YES', f'custom_commands_channel_added_{mode}', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @custom_commands_channel_list.command("remove")
    async def custom_commands_ignored_channels_remove(self, ctx, channel: TextChannel):
        channels = await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", 'CHANNELS')
        mode = "use" if await Configuration.get_var(ctx.guild.id, "CUSTOM_COMMANDS", "CHANNELS_IGNORED") else "ignore"
        if not channel.id in channels:
            await MessageUtils.send_to(ctx, 'NO', f'custom_commands_channel_not_on_{mode}_list',
                                       channel=channel.mention)
        else:
            channels.remove(channel.id)
            await MessageUtils.send_to(ctx, 'YES', f'custom_commands_channel_{mode}_removed', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @custom_commands_channel_list.command("mode")
    async def custom_commands_channel_list_mode(self, ctx, mode: ListMode):
        Configuration.set_var(ctx.guild.id, "CUSTOM_COMMANDS", "CHANNELS_IGNORED", mode)
        mode = "use" if mode else "ignore"
        await MessageUtils.send_to(ctx, "YES", f"custom_commands_channel_list_mode_{mode}")

    @custom_commands_role_list.command("mode")
    async def custom_commands_role_list_mode(self, ctx, mode: ListMode):
        Configuration.set_var(ctx.guild.id, "CUSTOM_COMMANDS", "ROLE_REQUIRED", mode)
        mode = "allowed" if mode else "blocked"
        await MessageUtils.send_to(ctx, "YES", f"custom_commands_role_list_mode_{mode}")

    @configure.command()
    async def custom_commands_mod_bypass(self, ctx, value: bool):
        """custom_commands_mod_bypass_help"""
        Configuration.set_var(ctx.guild.id, "CUSTOM_COMMANDS", "MOD_BYPASS", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('custom_commands_mod_bypass_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")

    anti_spam_types = {
        "duplicates",
        "duplicates_across_users",
        "max_messages",
        "max_newlines",
        "max_mentions",
        "max_links",
        "max_emoji",
        "censored",
        "voice_joins",
        "max_ghost_pings",
        "max_ghost_messages",
        "max_failed_mass_pings"
    }

    anti_spam_punishments = [
        "mute",
        "kick",
        "temp_ban",
        "ban"
    ]

    @configure.group(invoke_without_command=True)
    async def anti_spam(self, ctx):
        """anti_spam_help"""
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=await self.get_anti_spam_embed(ctx))

    async def get_anti_spam_embed(self, ctx):
        buckets = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "BUCKETS")
        embed = disnake.Embed()
        limit = Translator.translate("limit", ctx)
        timeframe = Translator.translate("timeframe", ctx)
        punishment = Translator.translate("punishment", ctx)
        disabled = Translator.translate("disabled", ctx)
        seen = set()
        for bucket in buckets:
            extra = ""
            if "DURATION" in bucket["PUNISHMENT"]:
                extra = f"for {Utils.to_pretty_time(bucket['PUNISHMENT']['DURATION'], ctx)}"
            desc = f"**{limit}**: {bucket['SIZE']['COUNT']}\n**{timeframe}**: {bucket['SIZE']['PERIOD']}s\n**{punishment}**: {bucket['PUNISHMENT']['TYPE']} {extra}"
            embed.add_field(name=bucket['TYPE'], value=desc)
            seen.add(bucket['TYPE'])
        for other in self.anti_spam_types - seen:
            embed.add_field(name=other, value=disabled)

        users = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_USERS")
        desc = None
        if len(users) == 0:
            desc = Translator.translate('no_ignored_spammers', ctx)
        else:
            resolved_users = [await Utils.get_user(user) for user in users if user is not None]
            desc = "\n".join(f"{str(user)} (`{user.id}`)" for user in resolved_users)
        embed.add_field(name=Translator.translate('ignored_spammers', ctx), value=desc)

        roles = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_ROLES")
        if len(roles) == 0:
            desc = Translator.translate('no_ignored_roles', ctx)
        else:
            desc = "\n".join(f"<@&{role}>" for role in roles)
        embed.add_field(name=Translator.translate('ignored_roles', ctx), value=desc)

        embed.set_footer(text=Translator.translate("mods_are_immune", ctx),
                         icon_url='https://cdn.discordapp.com/emojis/585877748996636674.png?v=1')

        return embed

    @anti_spam.command()
    async def set(self, ctx, type: SpamType, amount: RangedInt(2, 150), seconds: RangedInt(1, 180),
                  punishment: AntiSpamPunishment, duration: Duration = None):
        """anti_spam_set_help"""
        duration_required = punishment in ("mute", "temp_ban")
        if duration_required is (duration is None):
            await MessageUtils.send_to(ctx, 'NO', 'duration_required' if duration_required else "no_duration_expected")
            return

        Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "ENABLED", True)
        Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "CLEAN", True)

        existing = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "BUCKETS")

        new = {
            "TYPE": type,
            "SIZE": {
                "COUNT": amount,
                "PERIOD": seconds
            },
            "PUNISHMENT": {
                "TYPE": punishment
            }
        }
        if duration is not None:
            new["PUNISHMENT"]["DURATION"] = duration.to_seconds(ctx)

        for i in range(0, len(existing)):
            if existing[i]["TYPE"] == type:
                existing[i] = new
                break
        else:
            existing.append(new)

        Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "BUCKETS", existing)

        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('anti_spam_updated', ctx)}",
                       embed=await self.get_anti_spam_embed(ctx))

    @anti_spam.command("disable")
    async def anti_spam_disable(self, ctx, type: SpamType):
        """anti_spam_disable_help"""
        existing = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "BUCKETS")
        for i in range(0, len(existing)):
            if existing[i]["TYPE"] == type:
                del existing[i]
                break
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('anti_spam_updated', ctx)}",
                       embed=await self.get_anti_spam_embed(ctx))
        Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "BUCKETS", existing)

    @anti_spam.group("immune_users", invoke_without_command=True)
    async def immune_users(self, ctx):
        """anti_spam_immune_users_help"""
        pass

    @immune_users.command("add")
    async def immune_users_add(self, ctx, member: disnake.Member):
        """anti_spam_immune_users_add_help"""
        users = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_USERS")
        if member.id in users:
            await MessageUtils.send_to(ctx, 'NO', 'already_immune', user=Utils.clean_user(member))
        else:
            users.append(member.id)
            Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_USERS", users)
            message = MessageUtils.assemble(ctx, "YES", "user_made_immune", user=Utils.clean_user(member))
            await ctx.send(message, embed=await self.get_anti_spam_embed(ctx))

    @immune_users.command("remove")
    async def immune_users_remove(self, ctx, mid: int):
        """anti_spam_immune_users_remove_help"""
        users = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_USERS")
        user = await Utils.get_user(mid)
        uname = Utils.clean_user(user)  if user is not None else mid
        if mid not in users:
            await MessageUtils.send_to(ctx, 'NO', 'user_not_immune', user=uname)
        else:
            users.remove(mid)
            Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_USERS", users)
            message = MessageUtils.assemble(ctx, "YES", "user_no_longer_immune", user=uname)
            await ctx.send(message, embed=await self.get_anti_spam_embed(ctx))

    @anti_spam.group("immune_roles", invoke_without_command=True)
    async def immune_roles(self, ctx):
        """anti_spam_immune_roles_help"""
        pass

    @immune_roles.command("add")
    async def immune_roles_add(self, ctx, role: disnake.Role):
        """anti_spam_immune_roles_add_help"""
        roles = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_ROLES")
        if role.id in roles:
            await MessageUtils.send_to(ctx, 'NO', 'role_already_immune', role=role.name)
        else:
            roles.append(role.id)
            Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_ROLES", roles)
            message = MessageUtils.assemble(ctx, "YES", "role_made_immune", role=role.name)
            await ctx.send(message, embed=await self.get_anti_spam_embed(ctx))

    @immune_roles.command("remove")
    async def immune_roles_roles(self, ctx, role: int):
        """anti_spam_immune_roles_remove_help"""
        roles = await Configuration.get_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_ROLES")
        r = ctx.guild.get_role(role)
        if role not in roles:
            await MessageUtils.send_to(ctx, 'NO', 'role_not_immune', role=r.name if r is not None else role)
        else:
            roles.remove(role)
            Configuration.set_var(ctx.guild.id, "ANTI_SPAM", "EXEMPT_ROLES", roles)
            message = MessageUtils.assemble(ctx, "YES", "role_no_longer_immune", role=r.name if r is not None else role)
            await ctx.send(message, embed=await self.get_anti_spam_embed(ctx))

    @configure.command(aliases=["trustedcensorbypass"])
    async def trusted_censor_bypass(self, ctx: commands.Context, enabled_status: bool):
        """trustedcensorbypass_help"""
        config_status = await Configuration.get_var(ctx.guild.id, "CENSORING", "ALLOW_TRUSTED_CENSOR_BYPASS")

        enabled_string = "enabled" if enabled_status else "disabled"
        enabled_string = Translator.translate(enabled_string, ctx.guild.id)

        if enabled_status == config_status:
            message = MessageUtils.assemble(ctx, "NO", f"actual_censor_trusted_bypass_unchanged", status=enabled_string)
        else:
            message = MessageUtils.assemble(ctx, "YES", "actual_censor_trusted_bypass", status=enabled_string)
            Configuration.set_var(ctx.guild.id, "CENSORING", "ALLOW_TRUSTED_CENSOR_BYPASS", enabled_status)
        await ctx.send(message)

    @configure.command(aliases=["trustedflagbypass"])
    async def trusted_flag_bypass(self, ctx: commands.Context, enabled_status: bool):
        """trustedflagbypass_help"""
        config_status = await Configuration.get_var(ctx.guild.id, "FLAGGING", "TRUSTED_BYPASS")

        enabled_string = "enabled" if enabled_status else "disabled"
        enabled_string = Translator.translate(enabled_string, ctx.guild.id)

        if enabled_status == config_status:
            message = MessageUtils.assemble(ctx, "NO", f"actual_flag_trusted_bypass_unchanged", status=enabled_string)
        else:
            message = MessageUtils.assemble(ctx, "YES", "flag_trusted_bypass", status=enabled_string)
            Configuration.set_var(ctx.guild.id, "FLAGGING", "TRUSTED_BYPASS", enabled_status)
        await ctx.send(message)

    @configure.command(aliases=["gmt"])
    async def ghost_message_threshold(self, ctx, threshold: RangedInt(1, 60) = None):
        """ghost_message_threshold_help"""
        current = await Configuration.get_var(ctx.guild.id, "GENERAL", "GHOST_MESSAGE_THRESHOLD")
        if threshold is None:
            await MessageUtils.send_to(ctx, 'WRENCH', 'ghost_message_threshold_current', threshold=current)
        elif current != threshold:
            Configuration.set_var(ctx.guild.id, "GENERAL", "GHOST_MESSAGE_THRESHOLD", threshold)
            await MessageUtils.send_to(ctx, 'YES', 'ghost_message_threshold_current', threshold=threshold)
        else:
            await MessageUtils.send_to(ctx, 'WARNING', 'ghost_message_threshold_unchanged', threshold=threshold)

    @configure.command(aliases=["gpt"])
    async def ghost_ping_threshold(self, ctx, threshold: RangedInt(1, 60) = None):
        """ghost_ping_threshold_help"""
        current = await Configuration.get_var(ctx.guild.id, "GENERAL", "GHOST_PING_THRESHOLD")
        if threshold is None:
            await MessageUtils.send_to(ctx, 'WRENCH', 'ghost_ping_threshold_current', threshold=current)
        elif current != threshold:
            Configuration.set_var(ctx.guild.id, "GENERAL", "GHOST_PING_THRESHOLD", threshold)
            await MessageUtils.send_to(ctx, 'YES', 'ghost_ping_threshold_current', threshold=threshold)
        else:
            await MessageUtils.send_to(ctx, 'WARNING', 'ghost_message_threshold_unchanged', threshold=threshold)

    @configure.command()
    async def ignore_ids_for_censoring(self, ctx, value: bool = None):
        current = await Configuration.get_var(ctx.guild.id, 'CENSORING', 'IGNORE_IDS')
        if value is None:
            await MessageUtils.send_to(ctx, 'WRENCH',
                                       f'censoring_ignore_ids_is_' + ('enabled' if current else 'disabled'))
        elif current != value:
            Configuration.set_var(ctx.guild.id, 'CENSORING', 'IGNORE_IDS', value)
            await MessageUtils.send_to(ctx, 'YES', f'censoring_ignore_ids_' + ('enabled' if value else 'disabled'))
        else:
            await MessageUtils.send_to(ctx, 'WARNING',
                                       f'censoring_ignore_ids_already_' + ('enabled' if value else 'disabled'))

    @configure.command()
    async def ignore_ids_for_flagging(self, ctx, value: bool = None):
        current = await Configuration.get_var(ctx.guild.id, 'FLAGGING', 'IGNORE_IDS')
        if value is None:
            await MessageUtils.send_to(ctx, 'WRENCH',
                                       f'flagging_ignore_ids_is_' + ('enabled' if current else 'disabled'))
        elif current != value:
            Configuration.set_var(ctx.guild.id, 'FLAGGING', 'IGNORE_IDS', value)
            await MessageUtils.send_to(ctx, 'YES', f'flagging_ignore_ids_' + ('enabled' if value else 'disabled'))
        else:
            await MessageUtils.send_to(ctx, 'WARNING',
                                       f'flagging_ignore_ids_already_' + ('enabled' if value else 'disabled'))

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        changed = False
        for name in ["IGNORED_CHANNELS_CHANGES", "IGNORED_CHANNELS_OTHER"]:
            channels = await Configuration.get_var(channel.guild.id, "MESSAGE_LOGS", name)
            if channel.id in channels:
                channels.remove(channel.id)
                changed = True
        if changed:
            Configuration.save(channel.guild.id)

    @commands.cooldown(1, 3600, BucketType.guild)
    @commands.command(hidden=True)
    async def reset_guild_cache(self, ctx):
        if self.bot.is_ws_ratelimited():
            await MessageUtils.send_to(ctx, "LOADING", "guild_cache_reset_queued")
        while self.bot.is_ws_ratelimited():
            await asyncio.sleep(1)
        old = len(ctx.guild.members)
        await ctx.guild.chunk()
        new = len(ctx.guild.members)
        await MessageUtils.send_to(ctx, "LOADING", "guild_cache_reset_complete", old=old, new=new)




def setup(bot):
    bot.add_cog(ServerAdmin(bot))
