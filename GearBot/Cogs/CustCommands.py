import asyncio
from datetime import datetime

import discord
from discord.ext import commands

from Util import Permissioncheckers, Configuration
from database.DatabaseConnector import CustomCommand


class CustCommands:

    def __init__(self, bot):
        self.bot:commands.Bot = bot
        self.commands = dict()
        if self.bot.STARTUP_COMPLETE:
            self.reloadCommands()

    def __unload(self):
        #cleanup
        pass

    def __global_check(self, ctx):
        return True

    def __global_check_once(self, ctx):
        return True

    async def __local_check(self, ctx):
        return Permissioncheckers.isServerMod(ctx)

    async def on_ready(self):
        self.reloadCommands()

    def reloadCommands(self):
        for guild in self.bot.guilds:
            self.commands[guild.id] = dict()
            for command in CustomCommand.select().where(CustomCommand.serverid == guild.id):
                self.commands[guild.id][command.trigger] = command.response

    async def on_guild_join(self, guild):
        self.commands[guild.id] = dict()

    async def on_guild_remove(self, guild):
        del self.commands[guild.id]
        for command in CustomCommand.select().where(CustomCommand.serverid == guild.id):
            command.delete_instance()

    @commands.group(aliases=['commands'])
    @commands.guild_only()
    async def command(self, ctx:commands.Context):
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(timestamp=datetime.now(), color=0x663399, title=f"Custom command list for {ctx.guild.name}")
            value = ""
            if len(self.commands[ctx.guild.id].keys()) > 0:
                for trigger in self.commands[ctx.guild.id].keys():
                    if len(value) + len(trigger) > 1000:
                        embed.add_field(name="\u200b", value=value)
                        value = ""
                    value = f"{value}{trigger}\n"
                embed.add_field(name="\u200b", value=value)
                await ctx.send(embed=embed)
            else:
                await ctx.send("No custom commands have been created yet")

    @command.command()
    @commands.guild_only()
    async def create(self, ctx:commands.Context, trigger:str, *, reply:str = None):
        if reply is None or reply == "":
            ctx.send("Please provide a response as well")
        else:
            command = CustomCommand.get_or_none(serverid = ctx.guild.id, trigger=trigger)
            if command is None:
                CustomCommand.create(serverid = ctx.guild.id, trigger=trigger, response=reply)
                self.commands[ctx.guild.id][trigger] = reply
                await ctx.send(f"Command `{trigger}` has been added")
            else:
                await ctx.send(f":warning: This command already exists, updating it with the new text")
                await ctx.invoke(self.update, trigger, reply=reply)

    @command.command()
    @commands.guild_only()
    async def remove(self, ctx:commands.Context, trigger:str):
        if trigger in self.commands[ctx.guild.id]:
            CustomCommand.get(serverid = ctx.guild.id, trigger=trigger).delete_instance()
            del self.commands[ctx.guild.id][trigger]
            await ctx.send(f"Command `{trigger}` has been removed")
        else:
            await ctx.send(f"Unable to remove ´{trigger}` as it doesn't seem to exist")

    @command.command()
    @commands.guild_only()
    async def update (self, ctx:commands.Context, trigger:str, *, reply:str = None):
        if reply is None:
            ctx.send("Please provide a response as well")
        else:
            command = CustomCommand.get_or_none(serverid = ctx.guild.id, trigger=trigger)
            if command is None:
                await ctx.send(f":warning: This command does not exist, making it for you instead")
                await ctx.invoke(self.create, trigger, response=reply)
            else:
                command.response = reply
                command.save()
                self.commands[ctx.guild.id][trigger] = reply
                await ctx.send(f"Command `{trigger}` has been updated")

    async def on_message(self, message: discord.Message):
        while not self.bot.STARTUP_COMPLETE:
            await asyncio.sleep(1)
        if message.channel.guild is None:
            return
        prefix = Configuration.getConfigVar(message.guild.id, "PREFIX")
        if message.content.startswith(prefix, 0):
            for trigger in self.commands[message.guild.id]:
                if message.content == prefix+trigger or (message.content.startswith(trigger, len(prefix)) and message.content[len(prefix+trigger)] == " "):
                    await message.channel.send(self.commands[message.guild.id][trigger])





def setup(bot):
    bot.add_cog(CustCommands(bot))