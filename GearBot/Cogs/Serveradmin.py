import discord
from discord.ext import commands
from discord.ext.commands import BadArgument

from Util import Configuration, Permissioncheckers


class Serveradmin:

    def __init__(self, bot):
        bot.to_cache = []
        self.bot = bot

    def __unload(self):
        pass

    async def __local_check(self, ctx:commands.Context):
        return Permissioncheckers.isServerAdmin(ctx)

    @commands.guild_only()
    @commands.group()
    async def configure(self, ctx:commands.Context):
        """Configure server specific settings"""
        if ctx.subcommand_passed is None:
            await ctx.send("See the subcommands (!help configure) for configurations")

    @configure.command()
    async def prefix(self, ctx:commands.Context, *, new_prefix:str = None):
        """Sets or show the server prefix"""
        if new_prefix is None:
            await ctx.send(f"The current server prefix is `{Configuration.getConfigVar(ctx.guild.id, 'PREFIX')}`")
        else:
            Configuration.setConfigVar(ctx.guild.id, "PREFIX", new_prefix)
            await ctx.send(f"The server prefix is now `{new_prefix}`")

    @configure.command()
    async def adminrole(self, ctx: commands.Context, roleID):
        """Sets the server admin role"""
        Configuration.setConfigVar(ctx.guild.id, "ADMIN_ROLE_ID", roleID)
        await ctx.send(f"The server admin role is now `{roleID}`")

    @configure.command()
    async def modrole(self, ctx: commands.Context, roleID):
        """Sets the role with moderation rights"""
        Configuration.setConfigVar(ctx.guild.id, "MOD_ROLE_ID", roleID)
        await ctx.send(f"The server moderation role is now `{roleID}`")

    @configure.command()
    async def muteRole(self, ctx:commands.Context, role:discord.Role):
        """Sets what role to use for mutes"""
        guild:discord.Guild = ctx.guild
        perms = guild.me.guild_permissions
        if not perms.manage_roles:
            await ctx.send("I require the 'manage_roles' permission to be able to add the role to people")
            return
        if not guild.me.top_role > role:
            await ctx.send(f"I need a role that is higher then the {role.mention} role to be able to add it to people")
            return
        Configuration.setConfigVar(ctx.guild.id, "MUTE_ROLE", int(role.id))
        await ctx.send(f"{role.mention} will now be used for muting people, denying send permissions for the role")
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
            message = f"I was unable to configure muting in the following channels, there probably is an explicit deny on that channel for 'manage channel' on those channels or their category (if they are synced) for one of my roles (includes everyone role). Please make sure i can manage those channels and run this command again or deny the `send_messages` and `add_reactions` permissions for {role.mention} manually\n"
            for fail in failed:
                if len(message) + len(fail) > 2048:
                    await ctx.send(message)
                    message = ""
                message = message + fail
            if len(message) > 0:
                await ctx.send(message)
        else:
            await ctx.send(f"Automatic mute setup complete")

    @configure.command()
    async def devRole(self, ctx:commands.Context, roleID):
        Configuration.setConfigVar(ctx.guild.id, "DEV_ROLE", roleID)
        await ctx.send(f"The server dev role has been set.")

    @configure.group()
    async def selfroles(self, ctx:commands.Context):
        """Allows adding/removing roles from the self assignable list"""
        if ctx.subcommand_passed is None:
            await ctx.send("Assignable roles")

    @selfroles.command()
    async def add(self, ctx:commands.Context, role:discord.Role):
        current = Configuration.getConfigVar(ctx.guild.id, "SELF_ROLES")
        if role.id in current:
            await ctx.send("This role is already assignable")
        else:
            current.append(role.id)
            Configuration.setConfigVar(ctx.guild.id, "SELF_ROLES", current)
            await ctx.send(f"The {role.name} role is now assignable")
            
    @selfroles.command()
    async def remove(self, ctx:commands.Context, role:discord.Role):
        current = Configuration.getConfigVar(ctx.guild.id, "SELF_ROLES")
        if role.id not in current:
            await ctx.send("This wasn't assignable")
        else:
            current.remove(role.id)
            Configuration.setConfigVar(ctx.guild.id, "SELF_ROLES", current)
            await ctx.send(f"The {role.name} role is now no longer assignable")

    @configure.group()
    async def ignoredUsers(self, ctx):
        """Configures users to ignore for edit/delete logs (like bots spamming the logs with edits"""
        pass

    @ignoredUsers.command(name="add")
    async def addIgnoredUser(self, ctx:commands.Context, user:discord.Member):
        current = Configuration.getConfigVar(ctx.guild.id, "IGNORED_USERS")
        if user.id in current:
            await ctx.send("This user is already ignored")
        else:
            current.append(user.id)
            Configuration.setConfigVar(ctx.guild.id, "IGNORED_USERS", current)
            await ctx.send("I will now no longer log this user's edited/deleted messages")

    @ignoredUsers.command(name="remove")
    async def removeIgnoredUser(self, ctx:commands.Context, user:discord.User):
        current = Configuration.getConfigVar(ctx.guild.id, "IGNORED_USERS")
        if user.id not in current:
            await ctx.send("This user was not on my ignore list")
        else:
            current.remove(user.id)
            Configuration.setConfigVar(ctx.guild.id, "IGNORED_USERS", current)
            await ctx.send("I will now no longer ignore this user's edited/deleted messages")

    @configure.command()
    async def joinLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for join/leave logs"""
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for join logs")
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages)")

    @configure.command()
    async def modLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for modlogs (mute/kick/ban/...)"""
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages:
            Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for mod logs")
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages)")

    @configure.command()
    async def minorLogChannel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Sets the logging channel for minor logs (edit/delete)"""
        if channel is None:
            raise BadArgument("Missing channel")
        permissions = channel.permissions_for(ctx.guild.get_member(self.bot.user.id))
        if permissions.read_messages and permissions.send_messages and permissions.embed_links:
            old = Configuration.getConfigVar(ctx.guild.id, "MINOR_LOGS")
            Configuration.setConfigVar(ctx.guild.id, "MINOR_LOGS", channel.id)
            await ctx.send(f"{channel.mention} will now be used for minor logs")
            if old == 0:
                await ctx.send(f"Caching recent messages for logging...")
                self.bot.to_cache.append(ctx)
        else:
            await ctx.send(
                f"I cannot use {channel.mention} for logging, i do not have the required permissions in there (read_messages, send_messages and embed_links)")

    @commands.group()
    @commands.guild_only()
    async def disable(self, ctx:commands.Context):
        """Base command for disabeling features"""
        pass

    @disable.command()
    async def mute(self, ctx:commands.Context):
        """Disable the mute feature"""
        role = discord.utils.get(ctx.guild.roles, id=Configuration.getConfigVar(ctx.guild.id, "MUTE_ROLE"))
        if role is not None:
            for member in role.members:
                await member.remove_roles(role, reason=f"Mute feature has been dissabled")
        Configuration.setConfigVar(ctx.guild.id, "MUTE_ROLE", 0)
        await ctx.send("Mute feature has been dissabled, all people muted have been unmuted and the role can now be removed")

    @disable.command(name="minorLogChannel")
    async def disableMinorLogChannel(self, ctx: commands.Context):
        """Disables minor logs (edit/delete)"""
        Configuration.setConfigVar(ctx.guild.id, "MINOR_LOGS", 0)
        await ctx.send("Minor logs have been dissabled")



    @disable.command(name="modLogChannel")
    async def disablemodLogChannel(self, ctx: commands.Context):
        """Disables the modlogs (mute/kick/ban/...)"""
        Configuration.setConfigVar(ctx.guild.id, "MOD_LOGS", 0)
        await ctx.send("Mod logs have been dissabled")

    @disable.command(name="joinLogChannel")
    async def disablejoinLogChannel(self, ctx: commands.Context):
        """Disables join/leave logs"""
        Configuration.setConfigVar(ctx.guild.id, "JOIN_LOGS", 0)
        await ctx.send("Join logs have been dissabled")




def setup(bot):
    bot.add_cog(Serveradmin(bot))