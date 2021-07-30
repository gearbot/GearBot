import time
from datetime import datetime

import discord
from discord import Interaction, ButtonStyle

from Util import MessageUtils, Translator, Utils
from database.DatabaseConnector import Reminder
from views.InfSearch import CallbackButton


class ReminderView(discord.ui.View):
    def __init__(self, guild_id, channel_id, reminder, user_id, timeout_callback, message_id, duration):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.timeout_callback = timeout_callback
        self.channel_id = channel_id
        self.reminder = reminder
        self.mid = message_id
        self.duration = duration
        self.guild_id = guild_id
        self.add_item(CallbackButton(label=Translator.translate('remind_option_dm', guild_id), callback=self.dm,
                                     style=ButtonStyle.blurple))
        self.add_item(CallbackButton(label=Translator.translate('remind_option_here', guild_id), callback=self.channel,
                                     style=ButtonStyle.blurple))
        self.add_item(
            CallbackButton(label=Translator.translate('cancel', guild_id), callback=self.cancel, style=ButtonStyle.red))

    async def on_timeout(self) -> None:
        await self.timeout_callback()

    async def dm(self, interaction: Interaction):
        if await self.execution_check(interaction):
            await Reminder.create(user_id=self.user_id, channel_id=self.channel_id, dm=True,
                                  to_remind=self.reminder,
                                  time=time.time() + self.duration, send=datetime.now().timestamp(),
                                  status=1,
                                  guild_id=self.guild_id, message_id=self.mid)
            await interaction.response.edit_message(content=MessageUtils.assemble(self.guild_id, "YES", f"reminder_confirmation_dm", duration=Utils.to_pretty_time(self.duration, self.guild_id)), view=None)
            self.stop()

    async def channel(self, interaction: Interaction):
        if await self.execution_check(interaction):
            await Reminder.create(user_id=self.user_id, channel_id=self.channel_id, dm=False,
                                  to_remind=self.reminder,
                                  time=time.time() + self.duration, send=datetime.now().timestamp(),
                                  status=1,
                                  guild_id=self.guild_id, message_id=self.mid)
            await interaction.response.edit_message(
                content=MessageUtils.assemble(self.guild_id, "YES", f"reminder_confirmation_here",
                                              duration=Utils.to_pretty_time(self.duration, self.guild_id)), view=None)
            self.stop()

    async def cancel(self, interaction: Interaction):
        if await self.execution_check(interaction):
            await interaction.response.edit_message(content=MessageUtils.assemble(self.guild_id, 'NO', 'command_canceled'), view=None)
            self.stop()

    async def execution_check(self, interaction: Interaction):
        if self.user_id == interaction.user.id:
            return True
        await self.refuse(interaction)
        return False

    async def refuse(self, interaction: Interaction):
        interaction.response.send_message(MessageUtils.assemble(self.guild_id, "NO", "wrong_interactor"),
                                          ephemeral=True)
