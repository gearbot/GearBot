import discord
from discord import Member
from discord.ext import commands

from Cogs.BaseCog import BaseCog
from Util import Configuration, Confirmation, Emoji, Translator, MessageUtils, Utils, Permissioncheckers
from database.DatabaseConnector import CustomCommand


class CustCommands(BaseCog):

    def __init__(self, bot):
        super().__init__(bot)

        self.commands = dict()
        self.bot.loop.create_task(self.reloadCommands())
        self.loaded = False


    async def reloadCommands(self):
        self.commands = dict()
        commands = await CustomCommand.all()
        for command in commands:
            if command.serverid not in self.commands:
                self.commands[command.serverid] = dict()
            self.commands[command.serverid][command.trigger] = command.response
        self.loaded = True

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        if guild.id in self.commands:
            del self.commands[guild.id]
            await CustomCommand.filter(serverid = guild.id).delete()


    @commands.group(name="commands", aliases=['command'])
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command(self, ctx:commands.Context):
        """custom_commands_help"""
        if ctx.invoked_subcommand is None:
            embed = discord.Embed(timestamp=ctx.message.created_at, color=0x663399, title=Translator.translate("custom_command_list", ctx.guild.id, server_name=ctx.guild.name))
            value = ""
            if ctx.guild.id in self.commands:
                for trigger in self.commands[ctx.guild.id].keys():
                    if len(value) + len(trigger) > 1000:
                        embed.add_field(name="\u200b", value=value)
                        value = ""
                    value = f"{value}{trigger}\n"
                embed.add_field(name="\u200b", value=value)
                await ctx.send(embed=embed)
            else:
                await ctx.send(Translator.translate("custom_command_no_commands", ctx.guild.id))

    @command.command(aliases=["new", "add"])
    @commands.guild_only()
    async def create(self, ctx: commands.Context, trigger: str, *, reply: str = None):
        """command_create_help"""
        if len(trigger) == 0:
            await ctx.send(f"{Emoji.get_chat_emoji('WHAT')} {Translator.translate('custom_command_empty_trigger', ctx.guild.id)}")
        elif reply is None or reply == "":
            await ctx.send(f"{Emoji.get_chat_emoji('WHAT')} {Translator.translate('custom_command_empty_reply', ctx.guild.id)}")
        elif len(trigger) > 20:
            await MessageUtils.send_to(ctx, 'WHAT', 'custom_command_trigger_too_long')
        else:
            trigger = trigger.lower()
            trigger = await Utils.clean(trigger)
            command = await CustomCommand.get_or_none(serverid=ctx.guild.id, trigger=trigger)
            if command is None:
                await CustomCommand.create(serverid = ctx.guild.id, trigger=trigger, response=reply)
                if ctx.guild.id not in self.commands:
                    self.commands[ctx.guild.id] = dict()
                self.commands[ctx.guild.id][trigger] = reply
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('custom_command_added', ctx.guild.id, trigger=trigger)}")
            else:
                async def yes():
                    await ctx.send(Translator.translate('updating', ctx.guild.id))
                    await ctx.invoke(self.update, trigger, reply=reply)
                async def no():
                    await ctx.send(Translator.translate('custom_command_not_updating', ctx.guild.id))
                await Confirmation.confirm(ctx, Translator.translate('custom_command_override_confirmation', ctx.guild.id), on_yes=yes , on_no=no)

    @command.command(aliases=["del", "delete"])
    @commands.guild_only()
    async def remove(self, ctx:commands.Context, trigger:str):
        """command_remove_help"""
        trigger = trigger.lower()
        trigger = await Utils.clean(trigger)
        if len(trigger) > 20:
            await MessageUtils.send_to(ctx, 'WHAT', 'custom_command_trigger_too_long')
        elif ctx.guild.id in self.commands and trigger in self.commands[ctx.guild.id]:
            await CustomCommand.filter(serverid = ctx.guild.id, trigger=trigger).delete()
            del self.commands[ctx.guild.id][trigger]
            await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('custom_command_removed', ctx.guild.id, trigger=trigger)}")
        else:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('custom_command_not_found', ctx.guild.id, trigger=trigger)}")

    @command.command(aliases=["edit", "set"])
    @commands.guild_only()
    async def update(self, ctx:commands.Context, trigger:str, *, reply:str = None):
        """command_update_help"""
        trigger = trigger.lower()
        trigger = await Utils.clean(trigger)
        if reply is None:
            await ctx.send(f"{Emoji.get_chat_emoji('NO')} {Translator.translate('custom_command_empty_reply', ctx)}")
        else:
            command = await CustomCommand.get_or_none(serverid = ctx.guild.id, trigger=trigger)
            if command is None:
                await ctx.send(f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('custom_command_creating', ctx.guild.id)}")
                await ctx.invoke(self.create, trigger, reply=reply)
            else:
                command.response = reply
                await command.save()
                self.commands[ctx.guild.id][trigger] = reply
                await ctx.send(f"{Emoji.get_chat_emoji('YES')} {Translator.translate('custom_command_updated', ctx.guild.id, trigger=trigger)}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not hasattr(message.channel, "guild") or message.channel.guild is None:
            return

        member = message.channel.guild.get_member(message.author.id)
        if member is None:
            return

        role_list = Configuration.get_var(message.guild.id, "CUSTOM_COMMANDS", "ROLES")
        role_required = Configuration.get_var(message.guild.id, "CUSTOM_COMMANDS", "ROLE_REQUIRED")
        channel_list = Configuration.get_var(message.guild.id, "CUSTOM_COMMANDS", "CHANNELS")
        channels_ignored = Configuration.get_var(message.guild.id, "CUSTOM_COMMANDS", "CHANNELS_IGNORED")
        mod_bypass = Configuration.get_var(message.guild.id, "CUSTOM_COMMANDS", "MOD_BYPASS")

        is_mod = Permissioncheckers.is_mod(member)

        if (message.channel.id in channel_list) is channels_ignored and not (is_mod and mod_bypass):
            return

        has_role = False
        for role in member.roles:
            if role.id in role_list:
                has_role = True
                break

        if has_role is not role_required:
            return

        prefix = Configuration.get_var(message.guild.id, "GENERAL", "PREFIX")
        if message.content.startswith(prefix, 0) and message.guild.id in self.commands:
            for trigger in self.commands[message.guild.id]:
                if message.content.lower() == prefix+trigger or (message.content.lower().startswith(trigger, len(prefix)) and message.content.lower()[len(prefix+trigger)] == " "):
                    command_content = self.commands[message.guild.id][trigger].replace("@", "@\u200b")
                    await message.channel.send(command_content)
                    self.bot.custom_command_count += 1





def setup(bot):
    bot.add_cog(CustCommands(bot))
