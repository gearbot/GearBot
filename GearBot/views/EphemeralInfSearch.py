import json

from discord import ButtonStyle, Interaction
from discord.ui import View, Button

from Util import Emoji, Utils, MessageUtils, InfractionUtils, Translator
from Util.InfractionUtils import fetch_infraction_pages, get_key
from views.Buttons import CallbackButton


class EphemeralInfSearch(View):
    def __init__(self, filters, pages, guild_id, userid, current_page=0):
        super().__init__(timeout=None)
        self.id=""
        if pages > 0:
            start = f"einf_search:{userid}:{current_page}"
                
            self.add_item(Button(label=Translator.translate('first_page', guild_id), custom_id=f'{start}:first_page', disabled=current_page == 0, style=ButtonStyle.blurple))
            self.add_item(Button(label=Translator.translate('prev_page', guild_id), custom_id=f'{start}:prev_page', disabled=current_page == 0, style=ButtonStyle.blurple))
            self.add_item(Button(emoji=Emoji.get_emoji('AE'), style=ButtonStyle.grey, custom_id=f'{start}:blank', label=None))
            self.add_item(Button(label=Translator.translate('next_page', guild_id), custom_id=f'{start}:next_page', disabled=current_page >= pages-1, style=ButtonStyle.blurple))
            self.add_item(Button(label=Translator.translate('last_page', guild_id), custom_id=f'{start}:last_page', disabled=current_page >= pages-1, style=ButtonStyle.blurple))
        self.stop()
        # self.add_item(CallbackButton(label='User', style=ButtonStyle.green if '[user]' in filters else ButtonStyle.red, cid=f'{start}:user', callback=self.on_toggle_user))
        # self.add_item(CallbackButton(label='Mod', style=ButtonStyle.green if '[mod]' in filters else ButtonStyle.red, cid=f'{start}:mod', callback=self.on_toggle_mod))
        # self.add_item(CallbackButton(label='reason', style=ButtonStyle.green if '[reason]' in filters else ButtonStyle.red, cid=f'{start}:reason', callback=self.on_toggle_reason))



async def get_ephemeral_cached_page(interaction, userid, new_page):
    key = get_key(interaction.guild_id, userid, ["[user]", "[mod]", "[reason]"], 100)
    count = await Utils.BOT.redis_pool.llen(key)
    page_num = new_page
    if count == 0:
        count = await fetch_infraction_pages(interaction.guild_id, userid, 100, ["[user]", "[mod]", "[reason]"],
                                             new_page)
        if page_num >= count:
            page_num = 0
        elif page_num < 0:
            page_num = count - 1
        page = (await Utils.BOT.wait_for("page_assembled", check=lambda l: l["key"] == key and l["page_num"] == page_num))["page"]
    else:
        if page_num == 1000:
            page_num = count-1
        elif page_num >= count:
            page_num = 0
        elif page_num < 0:
            page_num = count - 1
        page = await Utils.BOT.redis_pool.lindex(key, page_num)
    return page, page_num, count, userid, ["[user]", "[mod]", "[reason]"]
