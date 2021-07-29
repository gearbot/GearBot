import json

from discord import ButtonStyle, Interaction
from discord.ui import View, Button

from Util import Emoji, Utils, MessageUtils, InfractionUtils, Translator
from Util.InfractionUtils import fetch_infraction_pages, get_key
from views.Buttons import CallbackButton


class InfSearch(View):
    def __init__(self, filters, pages, guild_id, current_page=0):
        super().__init__(timeout=None)
        self.id=""
        if pages > 0:
            self.add_item(CallbackButton(Translator.translate('first_page', guild_id), self.on_first_page, 'inf_search:first_page', disabled=current_page == 0))
            self.add_item(CallbackButton(Translator.translate('prev_page', guild_id), self.on_prev_page, 'inf_search:prev_page', disabled=current_page == 0))
            self.add_item(CallbackButton(emoji=Emoji.get_emoji('AE'), style=ButtonStyle.grey, cid='inf_search:blank', callback=self.hi, label=None))
            self.add_item(CallbackButton(Translator.translate('next_page', guild_id), self.on_next_page, 'inf_search:next_page', disabled=current_page >= pages-1))
            self.add_item(CallbackButton(Translator.translate('last_page', guild_id), self.on_last_page, 'inf_search:last_page', disabled=current_page >= pages-1))
        # self.add_item(CallbackButton(label='User', style=ButtonStyle.green if '[user]' in filters else ButtonStyle.red, cid='inf_search:user', callback=self.on_toggle_user))
        # self.add_item(CallbackButton(label='Mod', style=ButtonStyle.green if '[mod]' in filters else ButtonStyle.red, cid='inf_search:mod', callback=self.on_toggle_mod))
        # self.add_item(CallbackButton(label='reason', style=ButtonStyle.green if '[reason]' in filters else ButtonStyle.red, cid='inf_search:reason', callback=self.on_toggle_reason))


    @staticmethod
    async def on_first_page(interaction: Interaction):
        page, current, pages, query, fields = await get_cached_page(interaction, 100)
        await interaction.response.edit_message(
            content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current, pages),
            view=InfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id)
        )


    @staticmethod
    async def on_prev_page(interaction: Interaction):
        page, current, pages, query, fields = await get_cached_page(interaction, -1)
        await interaction.response.edit_message(
            content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current, pages),
            view=InfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id)
        )

    @staticmethod
    async def on_next_page(interaction: Interaction):
        page, current, pages, query, fields = await get_cached_page(interaction, 1)
        await interaction.response.edit_message(
            content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current, pages),
            view=InfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id)
        )




    @staticmethod
    async def on_last_page(interaction: Interaction):
        page, current, pages, query, fields = await get_cached_page(interaction, -100)
        await interaction.response.edit_message(
            content=await InfractionUtils.assemble_message(interaction.guild_id, page, query, current, pages),
            view=InfSearch(filters=fields, pages=pages, current_page=current, guild_id=interaction.guild_id)
        )

    @staticmethod
    async def on_toggle_user(interaction: Interaction):
        pass

    @staticmethod
    async def on_toggle_mod(interaction: Interaction):
        pass

    @staticmethod
    async def on_toggle_reason(interaction: Interaction):
        pass

    @staticmethod
    async def hi(interaction: Interaction):
        await interaction.response.send_message(Emoji.get_chat_emoji('AE'), ephemeral=True)


async def get_meta(mid):
    return await Utils.BOT.redis_pool.get(f'inf_meta:{mid}')

async def get_cached_page(interaction: Interaction, diff):
    meta = await get_meta(interaction.message.id)
    if meta is None:
        await interaction.response.send_message(MessageUtils.assemble(interaction.guild_id, 'NO', 'no_longer_valid'),
                                                ephemeral=False)
        return
    m = json.loads(meta)
    key = get_key(interaction.guild_id, m['query'], m['fields'].split(' '), m['amount'])
    count = await Utils.BOT.redis_pool.llen(key)
    page_num = m['current_page'] + diff
    if count == 0:
        count = await fetch_infraction_pages(interaction.guild_id, m['query'], m['amount'], m['fields'].split(' '),
                                             meta['current_page'])
        if page_num >= count:
            page_num = 0
        elif page_num < 0:
            page_num = count - 1
        page = (await Utils.BOT.wait_for("page_assembled", check=lambda l: l["key"] == key and l["page_num"] == page_num))["page"]
    else:
        if page_num >= count:
            page_num = 0
        elif page_num < 0:
            page_num = count - 1
        page = await Utils.BOT.redis_pool.lindex(key, page_num)
    pipe = Utils.BOT.redis_pool.pipeline()
    m['current_page'] = page_num
    pipe.set(f"inf_meta:{interaction.message.id}", json.dumps(m))
    pipe.expire(f"inf_meta:{interaction.message.id}", 60 * 60 * 12)
    await pipe.execute()
    return page, page_num, count, m['query'], m['fields'].split(' ')
