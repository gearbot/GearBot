import discord
from discord.ext import commands

from Util import Configuration, Permissioncheckers, Emoji, Translator


class ServerHolder(object):
    sid = None
    name = None

    def __init__(self, sid):
        self.id = sid
        self.name = sid

async def add_item(ctx, item, item_type, list_name="roles"):
    roles = Configuration.getConfigVar(ctx.guild.id, f"{item_type}_{list_name}".upper())
    sname = list_name[:-1] if list_name[-1:] == "s" else list_name
    if item.id in roles:
        await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'already_{item_type}_{sname}', ctx, item=item.name)}")
    else:
        roles.append(item.id)
        Configuration.saveConfig(ctx.guild.id)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate(f'{item_type}_{sname}_added', ctx, item=item.name)}")


async def remove_item(ctx, item, item_type, list_name="roles"):
    roles = Configuration.getConfigVar(ctx.guild.id, f"{item_type}_{list_name}".upper())
    sname = list_name[:-1] if list_name[-1:] == "s" else list_name
    if item.id not in roles:
        await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate(f'was_no_{item_type}_{sname}', ctx, item=item.name)}")
    else:
        roles.remove(item.id)
        Configuration.saveConfig(ctx.guild.id)
        await ctx.send(
            f"{Emoji.get_chat_emoji('YES')} {Translator.translate(f'{item_type}_{sname}_removed', ctx, item=item.name)}")


async def list_list(ctx, item_type, list_name="roles", wrapper="<@&{item}>"):
    items = Configuration.getConfigVar(ctx.guild.id, f"{item_type}_{list_name}".upper())
    if len(items) == 0:
        desc = Translator.translate(f"no_{item_type}_{list_name}", ctx)
    else:
        desc = "\n".join(wrapper.format(item=item) for item in items)
    embed = discord.Embed(title=Translator.translate(f"current_{item_type}_{list_name}", ctx), description=desc)
    await ctx.send(embed=embed)


async def set_log_channel(ctx, channel, log_type, permissions=None):
    if permissions is None:
        permissions = ["read_messages", "send_messages"]
    channel_permissions = channel.permissions_for(ctx.guild.get_member(ctx.bot.user.id))
    if all(getattr(channel_permissions, perm) for perm in permissions):
        Configuration.setConfigVar(ctx.guild.id, f"{log_type}_LOGS".upper(), channel.id)
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {log_type}_log_channel_set", channel=channel.mention)
        return True
    else:
        await ctx.send(
            f"{Emoji.get_chat_emoji('NO')} {Translator.translate('missing_perms_in_channel', ctx, perms1=', '.join(permissions[:-1]), perms2=permissions[-1:])}")
        return False



class Serveradmin:
    critical = True

    def __init__(self, bot):
        bot.to_cache = []
        self.bot:commands.AutoShardedBot = bot
        self.validate_configs()

    def __unload(self):
        pass

    async def __local_check(self, ctx:commands.Context):
        return Permissioncheckers.is_admin(ctx)

    def validate_configs(self):
        for guild in self.bot.guilds:
            for type in ("TRUSTED", "MOD", "ADMIN"):
                to_remove = []
                roles = Configuration.getConfigVar(guild.id, type + "_ROLES")
                for role in roles:
                    if discord.utils.get(guild.roles, id=role) is None:
                        to_remove.append(role)
                for role in to_remove:
                    roles.remove(role)
            Configuration.saveConfig(guild.id)

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
            await ctx.send(f"{Translator.translate('current_server_prefix', ctx, prefix=Configuration.getConfigVar(ctx.guild.id, 'PREFIX'))}")
        elif len(new_prefix) > 25:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('prefix_too_long', ctx)}")
        else:
            Configuration.setConfigVar(ctx.guild.id, "PREFIX", new_prefix)
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
    async def add_mod_role(self, ctx, *,  role: discord.Role):
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
        """Sets what role to use for mutes"""
        guild:discord.Guild = ctx.guild
        perms = guild.me.guild_permissions
        if not perms.manage_roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_missing_perm', ctx)}")
            return
        if not guild.me.top_role > role:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('mute_missing_perm', ctx, role=role.mention)}")
            return
        Configuration.setConfigVar(ctx.guild.id, "MUTE_ROLE", int(role.id))
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
        await list_list(ctx, "ignored", "users", "<@{item}>")

    @ignored_users.command(name="add")
    async def addIgnoredUser(self, ctx:commands.Context, user:discord.Member):
        await add_item(ctx, user, "ignored", "users")

    @ignored_users.command(name="remove")
    async def removeIgnoredUser(self, ctx:commands.Context, user:discord.User):
        await remove_item(ctx, user, "ignored", "users")

    @configure.command()
    async def joinLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for join/leave logs"""


    @configure.command()
    async def modLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for modlogs (mute/kick/ban/...)"""
        await set_log_channel(ctx, channel, "mod")

    @configure.command()
    async def minorLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for minor logs (edit/delete)"""
        old = Configuration.getConfigVar(ctx.guild.id, "MINOR_LOGS")
        new = await set_log_channel(ctx, channel, "minor")
        if old == 0 and new:
            await ctx.send(Translator.translate('minor_log_caching_start', ctx))
            self.bot.to_cache.append(ctx)


    @configure.group()
    async def cog_overrides(self, ctx):
        if ctx.invoked_subcommand is self.cog_overrides:
            overrides = Configuration.getConfigVar(ctx.guild.id, "COG_OVERRIDES")
            if len(overrides) == 0:
                desc = Translator.translate('no_overrides', ctx)
            else:
                desc = "\n".join(f"{k}: {v} ({Translator.translate(f'perm_lvl_{v}')})" for k, v in overrides.items())
            embed = discord.Embed(color=6008770, title=Translator.translate('cog_overrides', ctx), description=desc)
            await ctx.send(embed=embed)

    perm_lvls = [
        "public",
        "trusted",
        "mod",
        "admin",
        "owner only",
        "disabled"
    ]

    @cog_overrides.command(name="add")
    async def add_cog_override(self, ctx, cog:str, perm_lvl:int):
        if cog in ctx.bot.cogs:
            cogo = ctx.bot.cogs[cog]
            if cogo.critical:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('core_cog_no_override', ctx, cog=cog)}")
            elif perm_lvl in range(6):
                if perm_lvl < cogo.cog_perm:
                    await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_min_perm_violation', ctx, cog=cog, min_lvl=cogo.cog_perm, min_lvl_name=Translator.translate(f'perm_lvl_{cogo.cog_perm}', ctx))}")
                else:
                    overrides = Configuration.getConfigVar(ctx.guild.id, "COG_OVERRIDES")
                    overrides[cog] = perm_lvl
                    Configuration.saveConfig(ctx.guild.id)
                    await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('cog_override_applied', ctx, cog=cog, perm_lvl=perm_lvl, perm_lvl_name=Translator.translate(f'perm_lvl_{perm_lvl}', ctx))}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('invalid_override_lvl', ctx)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_not_found', ctx)}")

    @cog_overrides.command(name="remove")
    async def remove_cog_override(self, ctx, cog: str):
        overrides = Configuration.getConfigVar(ctx.guild.id, "COG_OVERRIDES")
        if cog in overrides:
            del overrides[cog]
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('cog_override_removed', ctx, cog=cog)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('cog_override_not_found', ctx, cog=cog)}")

    @configure.group()
    async def command_overrides(self, ctx):
        if ctx.invoked_subcommand is self.command_overrides:
            overrides = Configuration.getConfigVar(ctx.guild.id, "COMMAND_OVERRIDES")
            if len(overrides) == 0:
                desc = Translator.translate('no_overrides', ctx)
            else:
                desc = "\n".join(f"{k}: {v} ({Translator.translate(f'perm_lvl_{v}')})" for k, v in overrides.items())
            embed = discord.Embed(color=6008770, title=Translator.translate('command_overrides', ctx), description=desc)
            await ctx.send(embed=embed)


    @command_overrides.command(name="add")
    async def add_command_override(self, ctx, command:str, perm_lvl:int):
        command_object = self.bot.get_command(command)
        if command_object is not None:
            cog = command_object.instance
            cog_name = command_object.cog_name
            if cog.critical:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} The {command} command is part of the {cog_name} core cog that does not allow permission overrides")
            elif perm_lvl in range(6):
                if perm_lvl < cog.cog_perm:
                    await ctx.send(f"{Emoji.get_chat_emoji('NO')} The {command} command is part of the {cog_name} cog that has a minimum permission lvl of {cog.cog_perm} ({self.perm_lvls[cog.cog_perm]})")
                else:
                    overrides = Configuration.getConfigVar(ctx.guild.id, "COMMAND_OVERRIDES")
                    overrides[command] = perm_lvl
                    Configuration.saveConfig(ctx.guild.id)
                    await ctx.send(f"{Emoji.get_chat_emoji('YES')} The {command} permission lvl is now set at {perm_lvl} ({self.perm_lvls[perm_lvl]})")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} Please specify a permissions value of 0 (public), 1 (trusted), 2 (mod), 3 (admin), 4 (server owner only) or 5 (disabled)")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find any command by that name")

    @command_overrides.command(name="remove")
    async def remove_command_override(self, ctx, command:str):
        overrides = Configuration.getConfigVar(ctx.guild.id, "COMMAND_OVERRIDES")
        if command in overrides:
            del overrides[command]
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} Command override for {command} has been removed.")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I don't have a command override for {command} to remove.")

    @configure.command()
    async def perm_denied_message(self, ctx, value:bool):
        Configuration.setConfigVar(ctx.guild.id, "PERM_DENIED_MESSAGE", value)
        await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('configure_perm_msg_' + ('enabled' if value else 'disabled'), ctx.guild.id)}")


    @configure.command()
    async def language(self, ctx, lang_code:str = None):
        """language_help"""
        if lang_code is None:
            await ctx.send(f"See https://crowdin.com/project/gearbot for all available languages and their translation statuses")
        else:
            if lang_code in Translator.LANGS:
                Configuration.setConfigVar(ctx.guild.id, "LANG", lang_code)
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('lang_changed', ctx.guild.id, lang=lang_code)}")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('MUTE')} {Translator.translate('lang_unknown', ctx.guild.id)}")

    @commands.group()
    @commands.guild_only()
    async def disable(self, ctx:commands.Context):
        """Base command for disabling features"""
        pass

    @disable.command()
    async def mute(self, ctx:commands.Context):
        """Disable the mute feature"""
        role = discord.utils.get(ctx.guild.roles, id=Configuration.getConfigVar(ctx.guild.id, "MUTE_ROLE"))
        if role is not None:
            for member in role.members:
                await member.remove_roles(role, reason=f"Mute feature has been disabled")
        Configuration.setConfigVar(ctx.guild.id, "MUTE_ROLE", 0)
        await ctx.send("Mute feature has been disabled, all people muted have been unmuted and the role can now be removed.")

    @disable.command(name="minorLogChannel")
    async def disableMinorLogChannel(self, ctx: commands.Context):
        """Disables minor logs (edit/delete)"""
        Configuration.setConfigVar(ctx.guild.id, "MINOR_LOGS", 0)
        await ctx.send("Minor logs have been disabled.")



    @disable.command(name="modLogChannel")
    async def disablemodLogChannel(self, ctx: commands.Context):
        """Disables the modlogs (mute/kick/ban/...)"""
        Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", 0)
        await ctx.send("Mod logs have been disabled.")

    @disable.command(name="joinLogChannel")
    async def disablejoinLogChannel(self, ctx: commands.Context):
        """Disables join/leave logs"""
        Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", 0)
        await ctx.send("Join logs have been disabled.")


def setup(bot):
    bot.add_cog(Serveradmin(bot))