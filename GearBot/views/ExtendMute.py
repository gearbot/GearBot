import discord
from discord import ButtonStyle

from Util import Translator
from views.Buttons import InvokerOnlyCallbackButton


class ExtendMuteView(discord.ui.View):
    def __init__(self, extend, until, overwrite, duration, guild_id, user_id):
        super().__init__(timeout=30)

        self.add_item(InvokerOnlyCallbackButton(user_id=user_id, guild_id=guild_id, label=Translator.translate('mute_option_extend', guild_id, duration=duration), callback=extend, style=ButtonStyle.blurple))
        self.add_item(InvokerOnlyCallbackButton(user_id=user_id, guild_id=guild_id, label=Translator.translate('mute_option_until', guild_id, duration=duration), callback=until, style=ButtonStyle.blurple))
        self.add_item(InvokerOnlyCallbackButton(user_id=user_id, guild_id=guild_id, label=Translator.translate('mute_option_overwrite', guild_id, duration=duration), callback=overwrite, style=ButtonStyle.blurple))
