import discord
from discord.ext import commands

from Util import Configuration, Permissioncheckers


class Serveradmin:

    def __init__(self, bot):
        self.bot = bot

    def __unload(self):
        pass

    async def __local_check(self, ctx:commands.Context):
        return Permissioncheckers.isServerAdmin(ctx)

    @commands.group()
    async def configure(self, ctx:commands.Context):
        """Configure server specific settings"""
        await ctx.send("See the subcommands (!help configure) for configurations")

    @configure.command()
    async def prefix(self, ctx:commands.Context, newPrefix):
        """Sets a new prefix for this server"""
        Configuration.setConfigVar(ctx.guild.id, "PREFIX", newPrefix)
        await ctx.send(f"The server prefix is now `{newPrefix}`")

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
        for channel in guild.text_channels:
            try:
                await channel.set_permissions(role, reason="Automatic mute role setup", send_messages=False, add_reactions=False)
            except discord.Forbidden as ex:
                await ctx.send(f"I was forbidden to setup {channel.mention}")
        for channel in guild.voice_channels:
            try:
                await channel.set_permissions(role, reason="Automatic mute role setup", speak=False, connect=False)
            except discord.Forbidden as ex:
                await ctx.send(f"I was forbidden to setup voice channel {channel.name}")

    @commands.group()
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




def setup(bot):
    bot.add_cog(Serveradmin(bot))