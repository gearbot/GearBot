from discord.ui import View, Button

from Util import Translator


class SimplePagerView(View):
    def __init__(self, guild_id, pages, page, t):
        super().__init__(timeout=None)
        set_components(self, pages, guild_id, page, t)
        self.stop()


def set_components(view, pages, guild_id, page, t):
    if pages > 2:
        view.add_item(
            Button(label=Translator.translate('first_page', guild_id), disabled=page == 0, custom_id=f"pager:0:{t}"))
    view.add_item(Button(label=Translator.translate('prev_page', guild_id), disabled=page == 0,
                         custom_id=f"pager:{page - 1}:{t}"))
    view.add_item(Button(label=Translator.translate('next_page', guild_id), disabled=page == pages - 1,
                         custom_id=f"pager:{page + 1}:{t}"))
    if pages > 2:
        view.add_item(Button(label=Translator.translate('last_page', guild_id), disabled=page == pages - 1,
                             custom_id=f"pager:{pages - 1}:{t}"))

def get_parts(pages, page_num, guild_id, t):
    if page_num == len(pages):
        page_num = 0
    view = None
    content = pages[page_num]
    if len(pages) > 1:
        view = SimplePagerView(guild_id, len(pages), page_num, t)
    return content, view, page_num
