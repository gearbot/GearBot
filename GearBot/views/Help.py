from discord import Interaction, ButtonStyle, SelectOption, SelectMenu
from discord.ui import Button, View, Select

from Cogs import BaseCog
from Util import Translator, Emoji, HelpGenerator, Utils, Pages
from views.Buttons import CallbackButton


class HelpView(View):
    def __init__(self, bot, guild_id, query, page, pages, with_select):
        super().__init__(timeout=None)
        set_components(self, guild_id, page, pages, query, bot, with_select)
        self.stop()


def set_components(view: View, guild_id, page, pages, query, bot, with_select):
    view.children.clear()
    if with_select:
        options = []
        options.append(SelectOption(label=Translator.translate('all', guild_id), value='None',
                                    description=Translator.translate('all_description', guild_id),
                                    default=query is None))
        for cog in bot.cogs:
            if cog in BaseCog.cog_permissions:
                options.append(SelectOption(label=cog, value=cog.lower(),
                                            description=Translator.translate('help_cog_description', guild_id, cog=cog),
                                            default=query == cog.lower()))
        view.add_item(Select(custom_id='help:selector', options=options))
    if pages > 1:
        view.add_item(
            Button(label=Translator.translate('first_page', guild_id), disabled=page == 0,
                   custom_id=f"help:page:0:{query}"))
        view.add_item(Button(label=Translator.translate('prev_page', guild_id), disabled=page == 0,
                             custom_id=f"help:page:0{page - 1}:{query}"))
        view.add_item(Button(label=Translator.translate('next_page', guild_id), disabled=page == pages - 1,
                             custom_id=f"help:page:{page + 1}:{query}"))
        view.add_item(Button(label=Translator.translate('last_page', guild_id), disabled=page == pages - 1,
                             custom_id=f"help:page:00{pages - 1}:{query}"))


async def message_parts(bot, query, guild, member, page_num):
    view = None
    raw_pages = await get_help_pages(query, guild, member, bot)
    if raw_pages is None:
        if query in [cog.lower() for cog in bot.cogs]:
            raw_pages = [Translator.translate('no_runnable_commands', guild)]
        else:
            return Translator.translate("help_not_found" if len(query) < 1500 else "help_no_wall_allowed", guild,
                                    query=await Utils.clean(query, emoji=False)), None
    if page_num >= len(raw_pages):
        page_num = 0
    eyes = Emoji.get_chat_emoji('EYES')
    content = f"{eyes} **{Translator.translate('help_title', guild, page_num=page_num + 1, pages=len(raw_pages))}** {eyes}```diff\n{raw_pages[page_num]}```"
    cog_names = [cog.lower() for cog in bot.cogs]
    if query is None or query.lower() in cog_names or len(raw_pages) > 1:
        view = HelpView(bot, guild, query, page_num, len(raw_pages), True)
    return content, view


async def get_help_pages(query, guild, member, bot):
    if query is None:
        return await HelpGenerator.command_list(bot, member, guild)
    else:
        for cog in bot.cogs:
            if query == cog.lower():
                return await HelpGenerator.gen_cog_help(bot, cog, member, guild)
        target = bot
        layers = query.split(" ")
        while len(layers) > 0:
            layer = layers.pop(0)
            if hasattr(target, "all_commands") and layer in target.all_commands.keys():
                target = target.all_commands[layer]
            else:
                target = None
                break
        if target is not None and target is not bot.all_commands:
            return await HelpGenerator.gen_command_help(bot, member, guild, target)
