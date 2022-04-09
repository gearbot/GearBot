from disnake import ButtonStyle, Interaction
from disnake.ui import Button

from Util import MessageUtils


class CallbackButton(Button):
    def __init__(self, label, callback, cid=None, disabled=False, emoji=None, style=ButtonStyle.blurple):
        super().__init__(style=style, label=label, custom_id=cid, disabled=disabled, emoji=emoji)
        self.to_callback = callback

    async def callback(self, interaction: Interaction):
        await self.to_callback(interaction)


class InvokerOnlyCallbackButton(Button):
    def __init__(self, user_id, guild_id, label, callback, cid=None, disabled=False, emoji=None, style=ButtonStyle.blurple):
        super().__init__(style=style, label=label, custom_id=cid, disabled=disabled, emoji=emoji)

        self.to_callback = callback
        self.user_id=user_id
        self.guild_id=guild_id

    async def callback(self, interaction: Interaction):
        if self.user_id == interaction.user.id:
            await self.to_callback(interaction)
            self.view.stop()
        else:
            interaction.response.send_message(MessageUtils.assemble(self.guild_id, "NO", "wrong_interactor"),
                                              ephemeral=True)
        await self.to_callback(interaction)