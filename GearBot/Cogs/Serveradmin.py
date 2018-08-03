import discord
from discord.ext import commands
from discord.ext.commands import BadArgument

from Util import Configuration, Permissioncheckers, Emoji


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
            await ctx.send(f"The current server prefix is `{Configuration.getConfigVar(ctx.guild.id, 'PREFIX')}`")
        elif len(new_prefix) > 25:
            await ctx.send("Please use a shorter prefix.")
        else:
            Configuration.setConfigVar(ctx.guild.id, "PREFIX", new_prefix)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} The server prefix is now `{new_prefix}`.")

    @configure.group()
    async def adminroles(self, ctx: commands.Context):
        """Show or configure server admin roles"""
        if ctx.invoked_subcommand is self.adminroles:
            roles = Configuration.getConfigVar(ctx.guild.id, "ADMIN_ROLES")
            if len(roles) == 0:
                desc = "No admin roles configured"
            else:
                desc = "\n".join(f"<@&{role}>" for role in roles)
            embed = discord.Embed(title="Current admin roles", description=desc)
            await ctx.send(embed=embed)

    @adminroles.command(name="add")
    async def add_admin_role(self, ctx, *, role:discord.Role):
        roles = Configuration.getConfigVar(ctx.guild.id, "ADMIN_ROLES")
        if role.id in roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} `{role.name}` is already an admin role")
        else:
            roles.append(role.id)
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} `{role.name}` is now an admin role")

    @adminroles.command(name="remove")
    async def remove_admin_role(self, ctx, *, role: discord.Role):
        roles = Configuration.getConfigVar(ctx.guild.id, "ADMIN_ROLES")
        if role.id not in roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} `{role.name}` was not an admin role so i cannot remove it")
        else:
            roles.remove(role.id)
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} `{role.name}` is no longer an admin role")



    @configure.group()
    async def modroles(self, ctx: commands.Context):
        """Show or configure server mod roles"""
        if ctx.invoked_subcommand is self.modroles:
            roles = Configuration.getConfigVar(ctx.guild.id, "MOD_ROLES")
            if len(roles) == 0:
                desc = "No mod roles configured"
            else:
                desc = "\n".join(f"<@&{role}>" for role in roles)
            embed = discord.Embed(title="Current admin roles", description=desc)
            await ctx.send(embed=embed)

    @modroles.command(name="add")
    async def add_mod_role(self, ctx, role: discord.Role):
        roles = Configuration.getConfigVar(ctx.guild.id, "MOD_ROLES")
        if role.id in roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} `{role.name}` is already a mod role")
        else:
            roles.append(role.id)
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} `{role.name}` is now a mod role")

    @modroles.command(name="remove")
    async def remove_mod_role(self, ctx, *, role: discord.Role):
        roles = Configuration.getConfigVar(ctx.guild.id, "MOD_ROLES")
        if role.id not in roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} `{role.name}` was not a mod role so i cannot remove it")
        else:
            roles.remove(role.id)
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} `{role.name}` is no longer a mod role")

    @configure.group()
    async def trustedroles(self, ctx: commands.Context):
        """Show or configure server trusted roles"""
        if ctx.invoked_subcommand is self.trustedroles:
            roles = Configuration.getConfigVar(ctx.guild.id, "TRUSTED_ROLES")
            if len(roles) == 0:
                desc = "No trusted roles configured"
            else:
                desc = "\n".join(f"<@&{role}>" for role in roles)
            embed = discord.Embed(title="Current admin roles", description=desc)
            await ctx.send(embed=embed)

    @trustedroles.command(name="add")
    async def add_trusted_role(self, ctx, role: discord.Role):
        roles = Configuration.getConfigVar(ctx.guild.id, "TRUSTED_ROLES")
        if role.id in roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} `{role.name}` is already a trusted role")
        else:
            roles.append(role.id)
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} `{role.name}` is now a trusted role")

    @trustedroles.command(name="remove")
    async def remove_trusted_role(self, ctx, *, role: discord.Role):
        roles = Configuration.getConfigVar(ctx.guild.id, "TRUSTED_ROLES")
        if role.id not in roles:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} `{role.name}` was not a trusted role so i cannot remove it")
        else:
            roles.remove(role.id)
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} `{role.name}` is no longer a trusted role")


    @configure.command()
    async def muteRole(self, ctx:commands.Context, role:discord.Role):
        """Sets what role to use for mutes"""
        guild:discord.Guild = ctx.guild
        perms = guild.me.guild_permissions
        if not perms.manage_roles:
            await ctx.send("I require the 'manage_roles' permission to be able to add the role to people.")
            return
        if not guild.me.top_role > role:
            await ctx.send(f"I need a role that is higher then the {role.mention} role to be able to add it to people.")
            return
        Configuration.setConfigVar(ctx.guild.id, "MUTE_ROLE", int(role.id))
        await ctx.send(f"{role.mention} will now be used for muting people, denying send permissions for the role.")
        failed = []
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(role, reason="Automatic mute role setup", send_messages=False, add_reactions=False)
            except discord.Forbidden as ex:
                failed.append(channel.mention)
        for channel in guild.voice_channels:
            try:
                await channel.set_permissions(role, reason="Automatic mute role setup", speak=False, connect=False)
            except discord.Forbidden as ex:
                failed.append(f"Voice channel {channel.name}")
        if len(failed) > 0:
            message = f"I was unable to configure muting in the following channels, there probably is an explicit deny on that channel for 'manage channel' on those channels or their category (if they are synced) for one of my roles (includes everyone role). Please make sure I can manage those channels and run this command again or deny the `send_messages` and `add_reactions` permissions for {role.mention} manually.\n"
            for fail in failed:
                if len(message) + len(fail) > 2048:
                    await ctx.send(message)
                    message = ""
                message = message + fail
            if len(message) > 0:
                await ctx.send(message)
        else:
            await ctx.send(f"Automatic mute setup complete.")

    @configure.group()
    async def selfroles(self, ctx:commands.Context):
        """Allows adding/removing roles from the self assignable list"""
        if ctx.subcommand_passed is None:
            await ctx.send("Assignable roles")

    @selfroles.command()
    async def add(self, ctx:commands.Context, role:discord.Role):
        current = Configuration.getConfigVar(ctx.guild.id, "SELF_ROLES")
        if role.id in current:
            await ctx.send("This role is already assignable.")
        else:
            current.append(role.id)
            Configuration.setConfigVar(ctx.guild.id, "SELF_ROLES", current)
            await ctx.send(f"The {role.name} role is now assignable.")

    @selfroles.command()
    async def remove(self, ctx:commands.Context, role:discord.Role):
        current = Configuration.getConfigVar(ctx.guild.id, "SELF_ROLES")
        if role.id not in current:
            await ctx.send("This wasn't assignable.")
        else:
            current.remove(role.id)
            Configuration.setConfigVar(ctx.guild.id, "SELF_ROLES", current)
            await ctx.send(f"The {role.name} role is now no longer assignable.")

    @configure.group()
    async def invite_whitelist(self, ctx: commands.Context):
        """Allows adding/removing servers from the invite whitelist, only enforced when there are servers on the list"""

    @invite_whitelist.command(name="add")
    async def add_to_whitelist(self, ctx: commands.Context, server:int):
        current = Configuration.getConfigVar(ctx.guild.id, "INVITE_WHITELIST")
        if server in current:
            await ctx.send("This server is already whitelisted.")
        else:
            current.append(server)
            Configuration.setConfigVar(ctx.guild.id, "INVITE_WHITELIST", current)
            await ctx.send(f"Server {server} is now whitelisted.")

    @invite_whitelist.command(name="remove")
    async def remove_from_whitelist(self, ctx: commands.Context, server:int):
        current = Configuration.getConfigVar(ctx.guild.id, "INVITE_WHITELIST")
        if server in current:
            await ctx.send("This server was not whitelisted.")
        else:
            current.remove(server)
            Configuration.setConfigVar(ctx.guild.id, "INVITE_WHITELIST", current)
            await ctx.send(f"Server {server} is no longer whitelisted.")

    @configure.group()
    async def ignoredUsers(self, ctx):
        """Configures users to ignore for edit/delete logs (like bots spamming the logs with edits"""
        pass

    @ignoredUsers.command(name="add")
    async def addIgnoredUser(self, ctx:commands.Context, user:discord.Member):
        current = Configuration.getConfigVar(ctx.guild.id, "IGNORED_USERS")
        if user.id in current:
            await ctx.send("This user is already ignored.")
        else:
            current.append(user.id)
            Configuration.setConfigVar(ctx.guild.id, "IGNORED_USERS", current)
            await ctx.send("I will now no longer log this user's edited/deleted messages.")

    @ignoredUsers.command(name="remove")
    async def removeIgnoredUser(self, ctx:commands.Context, user:discord.User):
        current = Configuration.getConfigVar(ctx.guild.id, "IGNORED_USERS")
        if user.id not in current:
            await ctx.send("This user was not on my ignore list.")
        else:
            current.remove(user.id)
            Configuration.setConfigVar(ctx.guild.id, "IGNORED_USERS", current)
            await ctx.send("I will now no longer ignore this user's edited/deleted messages.")

    @configure.command()
    async def joinLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for join/leave logs"""
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for join logs")
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, I do not have the required permissions in there (read_messages, send_messages).")

    @configure.command()
    async def modLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for modlogs (mute/kick/ban/...)"""
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for mod logs")
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, I do not have the required permissions in there (read_messages, send_messages).")

    @configure.command()
    async def minorLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for minor logs (edit/delete)"""
        if channel is None:
            raise BadArgument("Missing channel")
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages and permissions.embed_links:
            old = Configuration.getConfigVar(ctx.guild.id, "MINOR_LOGS")
            Configuration.setConfigVar(ctx.guild.id, "MINOR_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for minor logs.")
            if old == 0:
                await ctx.send(f"Caching recent messages for logging...")
                self.bot.to_cache.append(ctx)
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, I do not have the required permissions in there (read_messages, send_messages and embed_links).")


    @configure.group()
    async def cog_overrides(self, ctx):
        if ctx.invoked_subcommand is self.cog_overrides:
            overrides = Configuration.getConfigVar(ctx.guild.id, "COG_OVERRIDES")
            if len(overrides) == 0:
                desc = "No overrides"
            else:
                desc = "\n".join(f"{k}: {v} ({self.perm_lvls[v]})" for k, v in overrides.items())
            embed = discord.Embed(color=6008770, title="Command overrides", description=desc)
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
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} The {cog} cog is a core cog that does not allow permission overrides")
            elif perm_lvl in range(6):
                if perm_lvl < cogo.cog_perm:
                    await ctx.send(f"{Emoji.get_chat_emoji('NO')} The {cog} cog is has a minimum permission lvl of {cogo.cog_perm} ({self.perm_lvls[cogo.cog_perm]})")
                else:
                    overrides = Configuration.getConfigVar(ctx.guild.id, "COG_OVERRIDES")
                    overrides[cog] = perm_lvl
                    Configuration.saveConfig(ctx.guild.id)
                    await ctx.send(f"{Emoji.get_chat_emoji('YES')} The {cog} cog permission lvl is now set at {perm_lvl} ({self.perm_lvls[perm_lvl]})")
            else:
                await ctx.send(f"{Emoji.get_chat_emoji('NO')} Please specify a permissions value of 0 (public), 1 (trusted), 2 (mod), 3 (admin), 4 (server owner only) or 5 (disabled)")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I can't find any cog by that name")

    @cog_overrides.command(name="remove")
    async def remove_cog_override(self, ctx, cog: str):
        overrides = Configuration.getConfigVar(ctx.guild.id, "COG_OVERRIDES")
        if cog in overrides:
            del overrides[cog]
            Configuration.saveConfig(ctx.guild.id)
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} Cog override for {cog} has been removed.")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} I don't have a cog override for {cog} to remove.")

    @configure.group()
    async def command_overrides(self, ctx):
        if ctx.invoked_subcommand is self.command_overrides:
            overrides = Configuration.getConfigVar(ctx.guild.id, "COMMAND_OVERRIDES")
            if len(overrides) == 0:
                desc = "No overrides"
            else:
                desc = "\n".join(f"{k}: {v} ({self.perm_lvls[v]})" for k, v in overrides.items())
            embed = discord.Embed(color=6008770, title="Command overrides", description=desc)
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