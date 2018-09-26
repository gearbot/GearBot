import discord
from discord.ext import commands

from Util import Configuration, Permissioncheckers, Emoji, Translator, Features


class ServerHolder(object):
    sid = None
    name = None

    def __init__(self, sid):
        self.id = sid
        self.name = sid

async def add_item(ctx, item, item_type, list_name="roles"):
    roles = Configuration.get_var(ctx.guild.id, f"{item_type}_{list_name}".upper())
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


async def remove_item(ctx, item, item_type, list_name="roles"):
    roles = Configuration.get_var(ctx.guild.id, f"{item_type}_{list_name}".upper())
    sname = list_name[:-1] if list_name[-1:] == "s" else list_name
    if item.id not in roles:
        await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'was_no_{item_type}_{sname}', ctx, item=item.name)}")
    else:
        roles.remove(item.id)
        Configuration.save(ctx.guild.id)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate(f'{item_type}_{sname}_removed', ctx, item=item.name)}")


async def list_list(ctx, item_type, list_name="roles", wrapper="<@&{item}>"):
    items = Configuration.get_var(ctx.guild.id, f"{item_type}_{list_name}".upper())
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


class Serveradmin:
    permissions = {
        "min": 3,
        "max": 5,
        "required": 3,
        "commands": {
        }
    }

    LOGGING_TYPES = [
        "EDIT_LOGS", "NAME_CHANGES", "ROLE_CHANGES", "CENSORED_MESSAGES", "JOIN_LOGS", "MOD_ACTIONS", "COMMAND_EXECUTED",
        "FUTURE_LOGS"
    ]

    def __init__(self, bot):
        bot.to_cache = []
        self.bot:commands.AutoShardedBot = bot
        self.validate_configs()

    def __unload(self):
        pass

    async def __local_check(self, ctx:commands.Context):
        return Permissioncheckers.check_permission(ctx)

    def validate_configs(self):
        for guild in self.bot.guilds:
            for type in ("TRUSTED", "MOD", "ADMIN"):
                to_remove = []
                roles = Configuration.get_var(guild.id, type + "_ROLES")
                for role in roles:
                    if discord.utils.get(guild.roles, id=role) is None:
                        to_remove.append(role)
                for role in to_remove:
                    roles.remove(role)
            Configuration.save(guild.id)

    @commands.guild_only()
    @commands.group()
    async def configure(self, ctx:commands.Context):
        """configure_help"""
        if ctx.subcommand_passed is None:
            await ctx.send("See the subcommands (!help configure) for configurations.")

    @configure.command()
    async def prefix(self, ctx:commands.Context, *, new_prefix:str = None):
        """Sets or show the server prefix"""
        if new_prefix is None:
            await ctx.send(f"{Translator.translate('current_server_prefix', ctx, prefix=Configuration.get_var(ctx.guild.id, 'PREFIX'))}")
        elif len(new_prefix) > 25:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('prefix_too_long', ctx)}")
        else:
            Configuration.set_var(ctx.guild.id, "PREFIX", new_prefix)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('prefix_set', ctx, new_prefix=new_prefix)}")

    @configure.group(aliases=["adminroles"])
    async def admin_roles(self, ctx: commands.Context):
        """Show or configure server admin roles"""
        if ctx.invoked_subcommand is self.admin_roles:
            await list_list(ctx, 'admin')

    @admin_roles.command(name="add")
    async def add_admin_role(self, ctx, *, role:discord.Role):
        await add_item(ctx, role, 'admin')

    @admin_roles.command(name="remove")
    async def remove_admin_role(self, ctx, *, role: discord.Role):
        await remove_item(ctx, role, 'admin')

    @configure.group(aliases=["modroles"])
    async def mod_roles(self, ctx: commands.Context):
        """Show or configure server mod roles"""
        if ctx.invoked_subcommand is self.mod_roles:
            await list_list(ctx, 'mod')

    @mod_roles.command(name="add")
    async def add_mod_role(self, ctx, *, role: discord.Role):
        await add_item(ctx, role, 'mod')

    @mod_roles.command(name="remove")
    async def remove_mod_role(self, ctx, *, role: discord.Role):
        await remove_item(ctx, role, 'mod')

    @configure.group(aliases=["trustedroles"])
    async def trusted_roles(self, ctx: commands.Context):
        """Show or configure server trusted roles"""
        if ctx.invoked_subcommand is self.trusted_roles:
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
        Configuration.set_var(ctx.guild.id, "MUTE_ROLE", int(role.id))
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
                if len(message) + len(fail) > 2048:
                    await ctx.send(message)
                    message = ""
                message = message + fail
            if len(message) > 0:
                await ctx.send(message)
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('mute_setup_complete', ctx)}")

    @configure.group(aliases=["selfroles"])
    async def self_roles(self, ctx:commands.Context):
        """Allows adding/removing roles from the self assignable list"""
        if ctx.invoked_subcommand is self.self_roles:
            await list_list(ctx, 'self')

    @self_roles.command()
    async def add(self, ctx:commands.Context, *, role:discord.Role):
        await add_item(ctx, role, 'self')

    @self_roles.command()
    async def remove(self, ctx:commands.Context, *, role:discord.Role):
        await remove_item(ctx, role, 'self')

    @configure.group()
    async def invite_whitelist(self, ctx: commands.Context):
        """Allows adding/removing servers from the invite whitelist, only enforced when there are servers on the list"""
        if ctx.invoked_subcommand is self.invite_whitelist:
            await list_list(ctx, "invite", list_name="whitelist", wrapper="{item}")

    @invite_whitelist.command(name="add")
    async def add_to_whitelist(self, ctx: commands.Context, server:int):
        await add_item(ctx, ServerHolder(server), "invite", list_name="whitelist")

    @invite_whitelist.command(name="remove")
    async def remove_from_whitelist(self, ctx: commands.Context, server:int):
        await remove_item(ctx, ServerHolder(server), "invite", list_name="whitelist")

    @configure.group(aliases=["ignoredUsers"])
    async def ignored_users(self, ctx):
        """Configures users to ignore for edit/delete logs (like bots spamming the logs with edits"""
        if ctx.invoked_subcommand is self.ignored_users:
            await list_list(ctx, "ignored", "users", "<@{item}>")

    @ignored_users.command(name="add")
    async def addIgnoredUser(self, ctx:commands.Context, user:discord.Member):
        await add_item(ctx, user, "ignored", "users")

    @ignored_users.command(name="remove")
    async def removeIgnoredUser(self, ctx:commands.Context, user:discord.User):
        await remove_item(ctx, user, "ignored", "users")


    @configure.group()
    async def cog_overrides(self, ctx):
        """cog_overrides_help"""
        if ctx.invoked_subcommand is self.cog_overrides:
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

    @cog_overrides.command(name="add")
    async def add_cog_override(self, ctx, cog:str, perm_lvl:int):
        if cog in ctx.bot.cogs:
            cogo = ctx.bot.cogs[cog]
            if not hasattr(cogo, "permissions"):
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

    @cog_overrides.command(name="remove")
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
        if ctx.invoked_subcommand is self.command_overrides:
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
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog = command_object.instance
            cog_name = command_object.cog_name
            if not hasattr(cog, "permissions"):
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_core_cog_no_override', ctx, command=command, cog_name=cog_name)}")
            elif perm_lvl in range(7):
                perm_dict = Permissioncheckers.get_perm_dict(command.split(" "), cog.permissions)
                if perm_lvl < perm_dict["min"]:
                    lvl = cog.permissions['min']
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
                    override["required"] = perm_lvl
                    Configuration.save(ctx.guild.id)
                    await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('command_override_confirmation', ctx, command=command, perm_lvl=perm_lvl, perm_lvl_name=Translator.translate(f'perm_lvl_{perm_lvl}', ctx))}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('invalid_override_lvl', ctx)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('command_not_found', ctx)}")

    @command_overrides.command(name="remove")
    async def remove_command_override(self, ctx, command:str):
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog = command_object.instance
            cog_name = command_object.cog_name
            overrides = Configuration.get_var(ctx.guild.id, "PERM_OVERRIDES")
            found = False
            if cog_name in overrides:
                override = Permissioncheckers.get_perm_dict(command.split(" "), overrides[cog_name], True)
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
        Configuration.set_var(ctx.guild.id, "PERM_DENIED_MESSAGE", value)
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('configure_perm_msg_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")


    @configure.command()
    async def language(self, ctx, lang_code:str = None):
        """language_help"""
        if lang_code is None:
            await ctx.send(f"See https://crowdin.com/project/gearbot for all available languages and their translation statuses")
        else:
            if lang_code in Translator.LANGS:
                Configuration.set_var(ctx.guild.id, "LANG", lang_code)
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lang_changed', ctx.guild.id, lang=lang_code)}")
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
    async def logging(self, ctx):
        if ctx.invoked_subcommand is self.logging:
            embed = discord.Embed(color=6008770, title=Translator.translate('log_channels', ctx))
            channels = Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
            if len(channels) > 0:
                for cid, info in channels.items():
                    embed.add_field(name=cid, value=self.get_channel_properties(ctx, cid, info))

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
           channels[cid] = []
        info = channels[cid]
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
        embed.add_field(name=channel.id, value=self.get_channel_properties(ctx, channel.id, channels[cid]))
        await ctx.send(message, embed=embed)
        Configuration.save(ctx.guild.id)


    @logging.command(name="remove")
    async def remove_logging(self, ctx, channel: discord.TextChannel, *, types):
        cid = str(channel.id)
        channels = Configuration.get_var(ctx.guild.id, "LOG_CHANNELS")
        if cid not in channels:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('no_log_channel', ctx, channel=channel.mention)}")
        else:
            info = channels[cid]
            removed = []
            ignored = []
            known, unknown = self.extract_types(types)
            message = ""
            for t in known:
                if t in info:
                    removed.append(t)
                    info.remove(t)
                else:
                    ignored.append(t)
            if len(removed) > 0:
                message += f"{Emoji.get_chat_emoji('YES')} {Translator.translate('logs_disabled_channel', ctx, channel=channel.mention)}{', '.join(removed)}"

            if len(ignored) > 0:
                message += f"\n{Emoji.get_chat_emoji('WARNING')}{Translator.translate('logs_already_disabled_channel', ctx, channel=channel.mention)}{', '.join(ignored)}"

            if len(unknown) > 0:
                message += f"\n {Emoji.get_chat_emoji('NO')}{Translator.translate('logs_unknown', ctx)}{', '.join(unknown)}"

            embed = discord.Embed(color=6008770)
            embed.add_field(name=channel.id, value=self.get_channel_properties(ctx, channel.id, channels[cid]))
            await ctx.send(message, embed=embed)
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


    @logging.command(name="enable")
    async def enable_feature(self, ctx, types):
        enabled = []
        ignored = []
        known, unknown = self.extract_types(types)
        message = ""
        for t in known:
            if Configuration.get_var(ctx.guild.id, t):
                ignored.append(t)
            else:
                enabled.append(t)
                Configuration.set_var(ctx.guild.id, t, True)
                if t == "EDIT_LOGS":
                    await ctx.send(Translator.translate('minor_log_caching_start', ctx))
                    self.bot.to_cache.append(ctx)

        if len(enabled) > 0:
            message += f"{Emoji.get_chat_emoji('YES')} {Translator.translate('logs_enabled', ctx)}{', '.join(enabled)}"

        if len(ignored) > 0:
            message += f"\n{Emoji.get_chat_emoji('WARNING')}{Translator.translate('logs_already_enabled', ctx)}{', '.join(ignored)}"

        if len(unknown) > 0:
            message += f"\n {Emoji.get_chat_emoji('NO')}{Translator.translate('logs_unknown', ctx)}{', '.join(unknown)}"

        await ctx.send(message, embed=self.get_logging_status(ctx))

    @configure.group()
    @commands.guild_only()
    async def features(self, ctx):
        await ctx.send(embed=self.get_features_status(ctx))

    @staticmethod
    def get_features_status(ctx):
        enabled = f"{Emoji.get_chat_emoji('YES')} {Translator.translate('enabled', ctx)}"
        disabled = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('disabled', ctx)}"
        embed = discord.Embed(color=6008770, title=Translator.translate('features', ctx))
        for t in Features.requires_logging.values():
            e = Features.is_logged(ctx.guild.id, t)
            embed.add_field(name=t, value=enabled if e else disabled)
        return embed

    def can_remove(self, guild, feature):
        counts = dict()
        for cid, info in Configuration.get_var(guild, "LOG_CHANNELS").items():
            for i in info:
                if i not in counts:
                    counts[i] = 1
                else:
                    counts[i] +=1
        return feature in counts and counts[feature] > 1


    @features.command(name="disable")
    async def disable(self, ctx, feature:str, state:bool):
        feature = feature.upper()
        message = None
        if state:
            if not Features.can_enable(ctx.guild.id, feature):
                message = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('feature_missing_logging', ctx, type=Features.requires_logging[feature])}"
            elif Configuration.get_var(ctx.guild.id, feature):
                message = f"{Emoji.get_chat_emoji('NO')} {Translator.translate('feature_already_enabled', ctx)}"
            else:
                Configuration.set_var(ctx.guild.id, feature, state)
        else:
            pass

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


    @commands.group()
    @commands.guild_only()
    async def disable(self, ctx:commands.Context):
        """Base command for disabling features"""
        pass

    @disable.command()
    async def mute(self, ctx:commands.Context):
        """Disable the mute feature"""
        role = discord.utils.get(ctx.guild.roles, id=Configuration.get_var(ctx.guild.id, "MUTE_ROLE"))
        if role is not None:
            for member in role.members:
                await member.remove_roles(role, reason=f"Mute feature has been disabled")
        Configuration.set_var(ctx.guild.id, "MUTE_ROLE", 0)
        await ctx.send("Mute feature has been disabled, all people muted have been unmuted and the role can now be removed.")

    @configure.command()
    async def dm_on_warn(self, ctx, value: bool):
        """dm_on_warn_help"""
        Configuration.set_var(ctx.guild.id, "DM_ON_WARN", value)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate('dm_on_warn_msg_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")


def setup(bot):
    bot.add_cog(Serveradmin(bot))
