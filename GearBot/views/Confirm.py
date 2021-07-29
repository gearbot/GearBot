import discord
from discord import ButtonStyle, Interaction
from discord.ui import Button

from Util import  MessageUtils


class YesButton(Button['Confirm']):
    def __init__(self):
        super().__init__(style=ButtonStyle.green, label="Yes")

    async def callback(self, interaction: Interaction):
        await self.view.yes_callback(interaction)


class NoButton(Button):
    def __init__(self):
        super().__init__(style=ButtonStyle.red, label="No")

    async def callback(self, interaction: Interaction):
        await self.view.no_callback(interaction)


class Confirm(discord.ui.View):
    def __init__(self, guild_id, on_yes, on_no, on_timeout, check, timeout=30):
        super().__init__(timeout=timeout)
        self.add_item(YesButton())
        self.add_item(NoButton())
        self.guild_id = guild_id
        self.on_yes = on_yes
        self.on_no = on_no
        self.timeout_callback = on_timeout
        self.check = check

    async def on_timeout(self) -> None:
        await self.timeout_callback()

    async def yes_callback(self, interaction: Interaction):
        if await self.execution_check(interaction):
            await self.on_yes(interaction)
            self.stop()

    async def no_callback(self, interaction: Interaction):
        if await self.execution_check(interaction):
            await self.on_no(interaction)
            self.stop()

    async def execution_check(self, interaction: Interaction):
        if not self.check:
            return True
        if self.check(interaction):
            return True
        await self.refuse(interaction)
        return False

    async def refuse(self, interaction: Interaction):
        interaction.response.send_message(MessageUtils.assemble(self.guild_id, "NO", "wrong_interactor"),
                                          ephemeral=True)
