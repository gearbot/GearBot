import discord
import pytz
from discord import TextChannel
from discord.ext import commands
from pytz import UnknownTimeZoneError

from Cogs.BaseCog import BaseCog
from Util import Configuration, Permissioncheckers, Emoji, Translator, Features, Utils, Confirmation, Pages, \
    MessageUtils, Selfroles
from Util.Converters import LoggingChannel, ListMode


class ServerHolder(object):
    sid = None
    name = None

    def __init__(self, sid):
        self.id = sid
        self.name = sid


async def add_item(ctx, item, item_type, list_name="roles", config_section="PERMISSIONS"):
    target = f"{item_type}_{list_name}".upper()
    roles = Configuration.get_var(ctx.guild.id, config_section, target)
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
    roles = Configuration.get_var(ctx.guild.id, config_section, target)
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
    items = Configuration.get_var(ctx.guild.id, config_section, target)
    if len(items) == 0:
        desc = Translator.translate(f"no_{item_type}_{list_name}", ctx)
    else:
        desc = "\n".join(wrapper.format(item=item) for item in items)
    embed = discord.Embed(title=Translator.translate(f"current_{item_type}_{list_name}", ctx), description=desc)
    await ctx.send(embed=embed)


def gen_override_strings(ctx, perm_dict, prefix = ""):
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
        "FUTURE_LOGS"
    ]

    def __init__(self, bot):
        super().__init__(bot)

        bot.to_cache = []
        Pages.register("censorlist", self._censorlist_init, self._censorklist_update)
        Pages.register("word_censorlist", self._word_censorlist_init, self._word_censor_list_update)



    @commands.guild_only()
    @commands.group(aliases = ["config", "cfg"])
    async def configure(self, ctx:commands.Context):
        """configure_help"""
        if ctx.subcommand_passed is None:
            await ctx.send("See the subcommands (!help configure) for configurations.")

    @configure.command()
    async def prefix(self, ctx:commands.Context, *, new_prefix:str = None):
        """configure_prefix_help"""
        if new_prefix is None:
            await ctx.send(f"{Translator.translate('current_server_prefix', ctx, prefix=Configuration.get_var(ctx.guild.id, 'GENERAL', 'PREFIX'))}")
        elif len(new_prefix) > 25:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('prefix_too_long', ctx)}")
        else:
            Configuration.set_var(ctx.guild.id, "GENERAL", "PREFIX", new_prefix)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('prefix_set', ctx, new_prefix=new_prefix)}")

    @configure.group(aliases=["adminroles"])
    async def admin_roles(self, ctx: commands.Context):
        """configure_admin_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'admin')

    @admin_roles.command(name="add")
    async def add_admin_role(self, ctx, *, role:discord.Role):
        await add_item(ctx, role, 'admin')

    @admin_roles.command(name="remove")
    async def remove_admin_role(self, ctx, *, role: discord.Role):
        await remove_item(ctx, role, 'admin')

    @configure.group(aliases=["modroles"])
    async def mod_roles(self, ctx: commands.Context):
        """configure_mod_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'mod')

    @mod_roles.command(name="add")
    async def add_mod_role(self, ctx, *, role: discord.Role):
        await add_item(ctx, role, 'mod')

    @mod_roles.command(name="remove")
    async def remove_mod_role(self, ctx, *, role: discord.Role):
        await remove_item(ctx, role, 'mod')

    @configure.group(aliases=["trustedroles"])
    async def trusted_roles(self, ctx: commands.Context):
        """configure_trusted_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'trusted')

    @trusted_roles.command(name="add")
    async def add_trusted_role(self, ctx, *, role: discord.Role):
        await add_item(ctx, role, 'trusted')

    @trusted_roles.command(name="remove")
    async def remove_trusted_role(self, ctx, *, role: discord.Role):
        await remove_item(ctx, role, 'trusted')

    @configure.command(aliases=["muterole"])
    async def mute_role(self, ctx:commands.Context, role:discord.Role):
        """configure_mute_help"""
        if role == ctx.guild.default_role:
            return await ctx.send(
                f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'default_role_forbidden', ctx)}")
        guild:discord.Guild = ctx.guild
        perms = guild.me.guild_permissions
        if not perms.manage_roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_missing_perm', ctx)}")
            return
        if not guild.me.top_role > role:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_missing_perm', ctx, role=role.mention)}")
            return
        Configuration.set_var(ctx.guild.id, "ROLES", "MUTE_ROLE", int(role.id))
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('mute_role_confirmation', ctx, role=role.mention)}")
        failed = []
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(role, reason=Translator.translate('mute_setup', ctx), send_messages=False, add_reactions=False)
            except discord.Forbidden as ex:
                failed.append(channel.mention)
        for channel in guild.voice_channels:
            try:
                await channel.set_permissions(role, reason=Translator.translate('mute_setup', ctx), speak=False, connect=False)
            except discord.Forbidden as ex:
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

    @configure.group(aliases=["selfrole", "self_role"])
    async def self_roles(self, ctx:commands.Context):
        """configure_self_roles_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, 'self', config_section="ROLES")

    @self_roles.command()
    async def add(self, ctx:commands.Context, *, role:discord.Role):
        await add_item(ctx, role, 'self', config_section="ROLES")
        Selfroles.validate_self_roles(self.bot, ctx.guild)
        self.bot.dispatch("self_roles_update", ctx.guild.id)

    @self_roles.command()
    async def remove(self, ctx:commands.Context, *, role:discord.Role):
        await remove_item(ctx, role, 'self', config_section="ROLES")
        Selfroles.validate_self_roles(self.bot, ctx.guild)
        self.bot.dispatch("self_roles_update", ctx.guild.id)

    @configure.group()
    async def allowed_invites(self, ctx: commands.Context):
        """configure_allowed_invite_list_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, "allowed", list_name="invite_list", wrapper="{item}", config_section="CENSORING")

    @allowed_invites.command(name="add")
    async def add_to_allowed_list(self, ctx: commands.Context, server:int):
        await add_item(ctx, ServerHolder(server), "allowed", list_name="invite_list", config_section="CENSORING")

    @allowed_invites.command(name="remove")
    async def remove_from_allowed_list(self, ctx: commands.Context, server:int):
        await remove_item(ctx, ServerHolder(server), "allowed", list_name="invite_list", config_section="CENSORING")

    @configure.command(name="censortrustedbypass")
    async def enable_trusted_bypass(self, ctx: commands.Context, enabled_status: bool):
        config_status = Configuration.get_var(ctx.guild.id, "CENSORING", "ALLOW_TRUSTED_BYPASS")

        enabled_string = "enabled" if enabled_status else "disabled"
        enabled_string = Translator.translate(enabled_string, ctx.guild.id)

        message = MessageUtils.assemble(ctx, "YES", "censor_trusted_bypass", status=enabled_string)

        if enabled_status == config_status:
            message = MessageUtils.assemble(ctx, "NO", f"censor_trusted_bypass_unchanged", status=enabled_string)
        else:
            Configuration.set_var(ctx.guild.id, "CENSORING", "ALLOW_TRUSTED_BYPASS", enabled_status)

        await ctx.send(message)

    @configure.group(aliases=["ignoredUsers"])
    async def ignored_users(self, ctx):
        """configure_ignored_users_help"""
        if ctx.invoked_subcommand is None:
            await list_list(ctx, "ignored", "users", "<@{item}>", config_section="MESSAGE_LOGS")

    @ignored_users.command(name="add")
    async def addIgnoredUser(self, ctx:commands.Context, user:discord.Member):
        await add_item(ctx, user, "ignored", "users", config_section="MESSAGE_LOGS")

    @ignored_users.command(name="remove")
    async def removeIgnoredUser(self, ctx:commands.Context, user:discord.User):
        await remove_item(ctx, user, "ignored", list_name="users", config_section="MESSAGE_LOGS")


    @configure.group("cog_overrides")
    async def configure_cog_overrides(self, ctx):
        """cog_overrides_help"""
        if ctx.invoked_subcommand is None:
            overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            desc = ""
            for k, v in overrides.items():
                lvl = v["required"]
                if lvl >= 0:
                    desc += f"{k}: {lvl} ({Translator.translate(f'perm_lvl_{lvl}', ctx)})\n"
            if desc == "":
                desc = Translator.translate('no_overrides', ctx)
            embed = discord.Embed(color=6008770, title=Translator.translate('cog_overrides', ctx), description=desc)
            await ctx.send(embed=embed)

    @configure_cog_overrides.command(name="add")
    async def add_cog_override(self, ctx, cog:str, perm_lvl:int):
        cog = cog
        if cog in ctx.bot.cogs.keys():
            cogo = ctx.bot.cogs[cog]
            if cogo.permissions is None:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('core_cog_no_override', ctx, cog=cog)}")
            elif perm_lvl in range(7):
                min_lvl = cogo.permissions["min"]
                max_lvl = cogo.permissions["max"]
                if perm_lvl < min_lvl:
                    await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_min_perm_violation', ctx, cog=cog, min_lvl=min_lvl, min_lvl_name=Translator.translate(f'perm_lvl_{min_lvl}', ctx))}")
                elif perm_lvl > max_lvl:
                    await ctx.send(
                        f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_max_perm_violation', ctx, cog=cog, max_lvl=max_lvl, max_lvl_name=Translator.translate(f'perm_lvl_{max_lvl}', ctx))}")
                else:
                    overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
                    if cog not in overrides:
                        overrides[cog] = {
                            "required": perm_lvl,
                            "commands": {},
                            "people": []
                        }
                    else:
                        overrides[cog]["required"] = perm_lvl
                    Configuration.save(ctx.guild.id)
                    await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('cog_override_applied', ctx, cog=cog, perm_lvl=perm_lvl, perm_lvl_name=Translator.translate(f'perm_lvl_{perm_lvl}', ctx))}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('invalid_override_lvl', ctx)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_not_found', ctx)}")

    @configure_cog_overrides.command(name="remove")
    async def remove_cog_override(self, ctx, cog: str):
        overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
        if cog in overrides:
            overrides[cog]["required"] = -1
            Configuration.save(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('cog_override_removed', ctx, cog=cog)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_override_not_found', ctx, cog=cog)}")

    @configure.group()
    async def command_overrides(self, ctx):
        """command_overrides_help"""
        if ctx.invoked_subcommand is None:
            overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            embed = discord.Embed(color=6008770, title=Translator.translate('command_overrides', ctx))
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
    async def add_command_override(self, ctx, command:str, perm_lvl:int):
        command = command.lower()
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog = command_object.cog
            cog_name = command_object.cog_name
            if cog.permissions is None:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_core_cog_no_override', ctx, command=command, cog_name=cog_name)}")
            elif perm_lvl in range(7):
                perm_dict = Permissioncheckers.get_perm_dict(command_object.qualified_name.split(" "), cog.permissions)
                if perm_lvl < perm_dict["min"]:
                    lvl = perm_dict["min"]
                    await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_min_perm_violation', ctx, command=command, min_lvl=lvl, min_lvl_name=Translator.translate(f'perm_lvl_{lvl}', ctx))}")
                elif perm_lvl > perm_dict["max"]:
                    lvl = cog.permissions['max']
                    await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_max_perm_violation', ctx, command=command, max_lvl=lvl, max_lvl_name=Translator.translate(f'perm_lvl_{lvl}', ctx))}")
                else:
                    overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
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
                    await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('command_override_confirmation', ctx, command=command, perm_lvl=perm_lvl, perm_lvl_name=Translator.translate(f'perm_lvl_{perm_lvl}', ctx))}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('invalid_override_lvl', ctx)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_not_found', ctx)}")

    @command_overrides.command(name="remove")
    async def remove_command_override(self, ctx, command:str):
        command = command.lower()
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog_name = command_object.cog_name
            overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            found = False
            if cog_name in overrides:
                override = Permissioncheckers.get_perm_dict(command_object.qualified_name.split(" "), overrides[cog_name], True)
                if override is not None:
                    found = True
                    override["required"] = -1
                    Configuration.save(ctx.guild.id)
                    await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('command_override_removed', ctx, command=command)}")
            if not found:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_override_not_found', ctx, command=command)}")

    @configure.command()
    async def perm_denied_message(self, ctx, value:bool):
        """perm_denied_message_help"""
        Configuration.set_var(ctx.guild.id, "GENERAL", "PERM_DENIED_MESSAGE", value)
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('configure_perm_msg_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")


    @configure.command()
    async def language(self, ctx, lang_code:str = None):
        """language_help"""
        if lang_code is None:
            await ctx.send(f"See https://crowdin.com/project/gearbot for all available languages and their translation statuses")
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
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lang_changed', ctx.guild.id, lang=code, lang_name=Translator.LANG_NAMES[code])}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('lang_unknown', ctx.guild.id)}")

    @configure.group()
    async def lvl4(self, ctx):
        """lvl4_help"""
        pass

    @lvl4.command(name="add")
    async def add_lvl4(self, ctx, command:str, person:discord.Member):
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog_name = command_object.cog_name
            overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
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
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lvl4_added', ctx, member=person, command=command)}")
            else:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('already_had_lvl4', ctx, member=person, command=command)}")
            Configuration.save(ctx.guild.id)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_not_found', ctx)}")

    @lvl4.command(name="remove")
    async def remove_lvl4(self, ctx, command: str, person: discord.Member):
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog_name = command_object.cog_name
            overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            found = False
            if cog_name in overrides:
                lvl4_list = Permissioncheckers.get_perm_dict(command.split(" "), overrides[cog_name], strict=True)
                if lvl4_list is not None and person.id in lvl4_list["people"]:
                    found = True
            if found:
                lvl4_list["people"].remove(person.id)
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lvl4_removed', ctx, member=person, command=command)}")
                Configuration.save(ctx.guild.id)
            else:
                await ctx.send(
                    f"{Emoji.get_chat_emoji('NO')} {Translator.translate('did_not_have_lvl4', ctx, member=person, command=command)}")

    @configure.group()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def logging(self, ctx):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(color=6008770, title=Translator.translate('log_channels', ctx))
            channels = Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
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
                value += f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('missing_channel_perms', ctx, perms = ', '.join(missing))}\n\n"
        value += f"**{Translator.translate('to_be_logged', ctx)}** \n{', '.join(info)}\n\n"
        return value


    @logging.command(name="add")
    async def add_logging(self, ctx, channel:discord.TextChannel, *, types):
        cid = str(channel.id)
        channels = Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
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

        embed = discord.Embed(color=6008770)
        embed.add_field(name=channel.id, value=self.get_channel_properties(ctx, channel.id, channels[cid]["CATEGORIES"]))
        await ctx.send(message, embed=embed)
        Configuration.save(ctx.guild.id)

        features = []
        for a in added:
            feature = Utils.find_key(Features.requires_logging, a)
            if feature is not None and not Configuration.get_var(ctx.guild.id, feature):
                features.append(feature)

        if len(features) > 0:
            async def yes():
                await ctx.invoke(self.enable_feature, ", ".join(features))
            await Confirmation.confirm(ctx, MessageUtils.assemble(ctx.guild.id, 'WHAT', 'confirmation_enable_features', count=len(features)) + ', '.join(features), on_yes=yes)

    @logging.command(name="remove")
    async def remove_logging(self, ctx, cid: LoggingChannel, *, types):
        channel = self.bot.get_channel(int(cid))
        channels = Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
        if cid not in channels:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('no_log_channel', ctx, channel=f'<{cid}>')}")
        else:
            info = channels[cid]["CATEGORIES"]
            removed = []
            ignored = []
            unable = []
            known, unknown = self.extract_types(types)
            message = ""
            for t in known:
                if t in info:
                    if self.can_remove(ctx.guild.id, t):
                        removed.append(t)
                        info.remove(t)
                    else:
                        unable.append(t)
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
                embed = discord.Embed(color=6008770)
                embed.add_field(name=cid, value=self.get_channel_properties(ctx, cid, channels[cid]["CATEGORIES"]))
            else:
                embed=None
            await ctx.send(message, embed=embed)
            empty = []
            for cid, info in channels.items():
                if len(info) is 0:
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
        embed = discord.Embed(color=6008770, title=Translator.translate('log_types', ctx))
        for t in self.LOGGING_TYPES:
            e = Features.is_logged(ctx.guild.id, t)
            embed.add_field(name=t, value=enabled if e else disabled)
        return embed

    @configure.group()
    @commands.guild_only()
    async def features(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(embed=self.get_features_status(ctx))

    @features.command(name="enable")
    async def enable_feature(self, ctx, types):
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
            if Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED"):
                ignored.append(t)
            else:
                enabled.append(t)
                Configuration.set_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED", True)
                if t == "EDIT_LOGS":
                    await ctx.send(Translator.translate('minor_log_caching_start', ctx))
                    self.bot.to_cache.append(ctx)

        if len(enabled) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'YES', 'features_enabled', count=len(enabled)) + ', '.join(enabled)

        if len(ignored) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'WARNING', 'feature_already_enabled', count=len(ignored)) + ', '.join(ignored)

        if len(unknown) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'NO', 'logs_unknown', count=len(unknown)) + ', '.join(unknown)

        await ctx.send(message, embed=self.get_features_status(ctx))

    @staticmethod
    def get_features_status(ctx):
        enabled = f"{Emoji.get_chat_emoji('YES')} {Translator.translate('enabled', ctx)}"
        disabled = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('disabled', ctx)}"
        embed = discord.Embed(color=6008770, title=Translator.translate('features', ctx))
        for f, t in Features.requires_logging.items():
            e = Configuration.get_var(ctx.guild.id, t, "ENABLED", f)
            embed.add_field(name=f, value=enabled if e else disabled)
        return embed

    def can_remove(self, guild, logging):
        counts = dict()
        for cid, info in Configuration.get_var(guild, "LOG_CHANNELS").items():
            for i in info:
                if i not in counts:
                    counts[i] = 1
                else:
                    counts[i] +=1
        return logging not in Features.requires_logging.values() or (logging in counts and counts[logging] > 1) or Configuration.get_var("MESSAGE_LOGS" if logging == "EDIT_LOGS" else "CENSORING", "ENABLED", False)


    @features.command(name="disable")
    async def feature_disable(self, ctx, types:str):
        types = types.upper()
        disabled= []
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
            if not Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED"):
                ignored.append(t)
            else:
                disabled.append(t)
                Configuration.set_var(ctx.guild.id, "MESSAGE_LOGS" if t == "EDIT_LOGS" else "CENSORING", "ENABLED", False)

        if len(disabled) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'YES', 'features_disabled', count=len(disabled)) + ', '.join(disabled)

        if len(ignored) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'WARNING', 'feature_already_disabled', count=len(ignored)) + ', '.join(ignored)

        if len(unknown) > 0:
            message += MessageUtils.assemble(ctx.guild.id, 'NO', 'features_unknown', count=len(unknown)) + ', '.join(unknown)

        await ctx.send(message, embed=self.get_features_status(ctx))

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

    @configure.group()
    @commands.guild_only()
    async def ignored_channels(self, ctx):
        """ignored_channels_help"""
        if ctx.invoked_subcommand == self.ignored_channels:
            await ctx.invoke(self.bot.get_command("help"), query="configure ignored_channels")

    @ignored_channels.group("changes")
    @commands.guild_only()
    async def ignored_channels_changes(self, ctx):
        """ignored_channels_changes_help"""
        if ctx.invoked_subcommand == self.ignored_channels_changes:
            await ctx.invoke(self.bot.get_command("help"), query="configure ignored_channels changes")

    @ignored_channels_changes.command("add")
    async def ignored_channels_changes_add(self, ctx, channel:TextChannel):
        """ignored_channels_add_help"""
        channels = Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_CHANGES')
        if channel.id in channels:
            await MessageUtils.send_to(ctx, 'NO', 'ignored_channels_already_on_list')
        else:
            channels.append(channel.id)
            await MessageUtils.send_to(ctx, 'YES', 'ignored_channels_changes_added', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @ignored_channels_changes.command("remove")
    async def ignored_channels_changes_remove(self, ctx, channel: TextChannel):
        """ignored_channels_remove_help"""
        channels = Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_CHANGES')
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
        channel_list = Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", f'IGNORED_CHANNELS_{type.upper()}')
        if len(channel_list) > 0:
            channels = "\n".join(ctx.guild.get_channel(c).mention for c in channel_list)
        else:
            channels = Translator.translate('no_ignored_channels', ctx)
        embed = discord.Embed(color=ctx.guild.roles[-1].color, description=channels)
        embed.set_author(name=Translator.translate(f'ignored_channels_list_{type}', ctx, guild=ctx.guild.name), icon_url=ctx.guild.icon_url)
        await ctx.send(embed=embed)

    @ignored_channels.group("edits", aliases=["edit"])
    @commands.guild_only()
    async def ignored_channels_edits(self, ctx):
        """ignored_channels_edits_help"""
        if ctx.invoked_subcommand == self.ignored_channels_edits:
            await ctx.invoke(self.bot.get_command("help"), query="configure ignored_channels other")

    @ignored_channels_edits.command("add")
    async def ignored_channels_edits_add(self, ctx, channel: TextChannel):
        """ignored_channels_add_help"""
        channels = Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_OTHER')
        if channel.id in channels:
            await MessageUtils.send_to(ctx, 'NO', 'ignored_channels_already_on_list', channel=channel.mention)
        else:
            channels.append(channel.id)
            await MessageUtils.send_to(ctx, 'YES', 'ignored_channels_edits_added', channel=channel.mention)
            Configuration.save(ctx.guild.id)

    @ignored_channels_edits.command("remove")
    async def ignored_channels_edits_remove(self, ctx, channel: TextChannel):
        """ignored_channels_remove_help"""
        channels = Configuration.get_var(ctx.guild.id, "MESSAGE_LOGS", 'IGNORED_CHANNELS_OTHER')
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




    @commands.group()
    @commands.guild_only()
    async def disable(self, ctx:commands.Context):
        """disable_help"""
        pass

    @disable.command()
    async def mute(self, ctx:commands.Context):
        """disable_mute_help"""
        role = ctx.guild.get_role(Configuration.get_var(ctx.guild.id, "ROLES", "MUTE_ROLE"))
        if role is not None:
            for member in role.members:
                await member.remove_roles(role, reason=f"Mute feature has been disabled")
        Configuration.set_var(ctx.guild.id, "ROLES", "MUTE_ROLE", 0)
        await ctx.send("Mute feature has been disabled, all people muted have been unmuted and the role can now be removed.")

    @configure.command()
    async def dm_on_warn(self, ctx, value: bool):
        """dm_on_warn_help"""
        Configuration.set_var(ctx.guild.id, "INFRACTIONS", "DM_ON_WARN", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('dm_on_warn_msg_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")

    @configure.command()
    async def log_embeds(self, ctx, value: bool):
        Configuration.set_var(ctx.guild.id, "MESSAGE_LOGS", "EMBED", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('embed_log_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")

    @configure.group(aliases=["censorlist"])
    async def censor_list(self, ctx):
        if ctx.invoked_subcommand is None:
            await Pages.create_new(self.bot, "censor_list", ctx)

    @staticmethod
    async def _censorlist_init(ctx):
        pages = Pages.paginate("\n".join(Configuration.get_var(ctx.guild.id, "CENSORING", "TOKEN_CENSORLIST")))
        return f"**{Translator.translate(f'censor_list', ctx, server=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{pages[0]}```", None, len(pages) > 1

    @staticmethod
    async def _censorklist_update(ctx, message, page_num, action, data):
        pages = Pages.paginate("\n".join(Configuration.get_var(message.channel.guild.id, "CENSORING", "TOKEN_CENSORLIST")))
        page, page_num = Pages.basic_pages(pages, page_num, action)
        data["page"] = page_num
        return f"**{Translator.translate(f'censor_list', message.channel.guild.id, server=message.channel.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```", None, data

    @censor_list.command("add")
    async def censor_list_add(self, ctx, *, word: str):
        censor_list = Configuration.get_var(ctx.guild.id, "CENSORING", "TOKEN_CENSORLIST")
        if word.lower() in censor_list:
            await MessageUtils.send_to(ctx, "NO", "already_censored", word=word)
        else:
            censor_list.append(word.lower())
            await MessageUtils.send_to(ctx, "YES", "entry_added", entry=word)
            Configuration.save(ctx.guild.id)

    @censor_list.command("remove")
    async def censor_list_remove(self, ctx, *, word: str):
        censor_list = Configuration.get_var(ctx.guild.id, "CENSORING", "TOKEN_CENSORLIST")
        if word not in censor_list:
            await MessageUtils.send_to(ctx, "NO", "not_censored", word=word)
        else:
            censor_list.remove(word)
            await MessageUtils.send_to(ctx, "YES", "entry_removed", entry=word)
            Configuration.save(ctx.guild.id)

    @configure.group()
    async def word_censor_list(self, ctx):
        if ctx.invoked_subcommand is None:
            await Pages.create_new(self.bot, "word_censor_list", ctx)

    @staticmethod
    async def _word_censorlist_init(ctx):
        pages = Pages.paginate("\n".join(Configuration.get_var(ctx.guild.id, "CENSORING", "WORD_CENSORLIST")))
        return f"**{Translator.translate(f'censor_list', ctx, server=ctx.guild.name, page_num=1, pages=len(pages))}**```\n{pages[0]}```", None, len(
            pages) > 1

    @staticmethod
    async def _word_censor_list_update(ctx, message, page_num, action, data):
        pages = Pages.paginate(
            "\n".join(Configuration.get_var(message.channel.guild.id, "CENSORING", "WORD_CENSORLIST")))
        page, page_num = Pages.basic_pages(pages, page_num, action)
        data["page"] = page_num
        return f"**{Translator.translate(f'censor_list', message.channel.guild.id, server=message.channel.guild.name, page_num=page_num + 1, pages=len(pages))}**```\n{page}```", None, data

    @word_censor_list.command("add")
    async def word_censor_list_add(self, ctx, *, word: str):
        censor_list = Configuration.get_var(ctx.guild.id, "CENSORING", "WORD_CENSORLIST")
        if word.lower() in censor_list:
            await MessageUtils.send_to(ctx, "NO", "already_censored", word=word)
        else:
            censor_list.append(word.lower())
            await MessageUtils.send_to(ctx, "YES", "entry_added", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Censor").regexes:
                del self.bot.get_cog("Censor").regexes[ctx.guild.id]

    @word_censor_list.command("remove")
    async def word_censor_list_remove(self, ctx, *, word: str):
        censor_list = Configuration.get_var(ctx.guild.id, "CENSORING", "WORD_CENSORLIST")
        if word not in censor_list:
            await MessageUtils.send_to(ctx, "NO", "not_censored", word=word)
        else:
            censor_list.remove(word)
            await MessageUtils.send_to(ctx, "YES", "entry_removed", entry=word)
            Configuration.save(ctx.guild.id)
            if ctx.guild.id in self.bot.get_cog("Censor").regexes:
                del self.bot.get_cog("Censor").regexes[ctx.guild.id]


    @configure.group()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def role_list(self, ctx):
        """configure_role_list_help"""
        if ctx.invoked_subcommand is None:
            items = Configuration.get_var(ctx.guild.id, "ROLES", f"ROLE_LIST")
            mode = "allow" if Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE") else "block"
            if len(items) == 0:
                desc = Translator.translate(f"no_role_{mode}", ctx)
            else:
                desc = "\n".join(f"<@&{item}>" for item in items)
            embed = discord.Embed(title=Translator.translate(f"current_role_{mode}_list", ctx), description=desc)
            await ctx.send(embed=embed)

    @role_list.command("add")
    async def role_list_add(self, ctx, *, role:discord.Role):
        """configure_role_list_add"""
        roles = Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST")
        mode = "allow" if Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE") else "block"
        if role == ctx.guild.default_role:
            await MessageUtils.send_to(ctx, "NO", "default_role_forbidden")
        elif role.id in roles:
            await MessageUtils.send_to(ctx, "NO", f"role_list_add_fail", role=Utils.escape_markdown(role.name))
        else:
            roles.append(role.id)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"role_list_add_confirmation_{mode}", role=Utils.escape_markdown(role.name))


    @role_list.command("remove", aliases=["rmv"])
    async def role_list_remove(self, ctx, *, role: discord.Role):
        """configure_role_list_remove"""
        roles = Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST")
        mode = "allow" if Configuration.get_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE") else "block"
        if role.id not in roles:
            await MessageUtils.send_to(ctx, "NO", f"role_list_rmv_fail_{mode}", role=Utils.escape_markdown(role.name))
        else:
            roles.remove(role.id)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"role_list_rmv_confirmation_{mode}", role=Utils.escape_markdown(role.name))

    @role_list.command("mode")
    async def role_list_mode(self, ctx, mode:ListMode):
        """configure_role_list_mode"""
        Configuration.set_var(ctx.guild.id, "ROLES", "ROLE_LIST_MODE", mode)
        mode = "allowed" if mode else "blocked"
        await MessageUtils.send_to(ctx, "YES", f"role_list_mode_{mode}")



    @configure.group()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def domain_list(self, ctx):
        """configure_domain_list_help"""
        if ctx.invoked_subcommand is None:
            items = Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST")
            mode = "allowed" if Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED") else "blocked"
            if len(items) == 0:
                desc = Translator.translate(f"empty_domain_list", ctx)
            else:
                desc = "\n".join(f"{item}" for item in items)
            embed = discord.Embed(title=Translator.translate(f"current_domain_list_{mode}", ctx), description=desc)
            await ctx.send(embed=embed)

    @domain_list.command("add")
    async def domain_list_add(self, ctx, *, domain):
        """configure_domain_list_add"""
        domain = domain.lower()
        domains = Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST")
        mode = "allow" if Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED") else "block"
        if domain in domains:
            await MessageUtils.send_to(ctx, "NO", f"domain_list_add_fail_{mode}", domain=domain)
        else:
            domains.append(domain)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"domain_list_add_confirmation_{mode}", domain=domain)


    @domain_list.command("remove", aliases=["rmv"])
    async def domain_list_remove(self, ctx, *, domain):
        """configure_domain_list_remove"""
        domains = Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST")
        mode = "allow" if Configuration.get_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED") else "block"
        if domain not in domains:
            await MessageUtils.send_to(ctx, "NO", f"domain_list_rmv_fail_{mode}", domain=domain)
        else:
            domains.remove(domain)
            Configuration.save(ctx.guild.id)
            await MessageUtils.send_to(ctx, "YES", f"domain_list_rmv_confirmation_{mode}", domain=domain)

    @domain_list.command("mode")
    async def domain_list_mode(self, ctx, mode:ListMode):
        """configure_domain_list_mode"""
        Configuration.set_var(ctx.guild.id, "CENSORING", "DOMAIN_LIST_ALLOWED", mode)
        mode = "allow" if mode else "block"
        await MessageUtils.send_to(ctx, "YES", f"domain_list_mode_{mode}")

    @configure.command()
    @commands.guild_only()
    async def timezone(self, ctx, new_zone=None):
        """timezone_help"""
        current_zone = Configuration.get_var(ctx.guild.id, "GENERAL", "TIMEZONE")
        if new_zone is None:
            #no new zone, spit out the current one
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

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        changed = False
        for name in ["IGNORED_CHANNELS_CHANGES", "IGNORED_CHANNELS_OTHER"]:
            channels = Configuration.get_var(channel.guild.id, "MESSAGE_LOGS", name)
            if channel.id in channels:
                channels.remove(channel.id)
                changed = True
        if changed:
            Configuration.save(channel.guild.id)



def setup(bot):
    bot.add_cog(ServerAdmin(bot))
