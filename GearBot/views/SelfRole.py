import math

import disnake
from disnake import ButtonStyle, Interaction
from disnake.ui import Button

from Util import Translator, Configuration, Utils


class SelfRoleView(disnake.ui.View):
    def __init__(self, guild, page):
        super().__init__(timeout=None)
        set_buttons(self, guild, page)
        self.stop()

def set_buttons(view: disnake.ui.View, guild, page):
    view.children.clear()
    roles = [role for role in (guild.get_role(r) for r in Configuration.get_var(guild.id, "ROLES", "SELF_ROLES")) if
             role is not None]
    pages = [p for p in Utils.chunks(roles, 20)]
    view.pages = len(pages)
    if len(pages) == 0:
        return
    if page > len(pages) or page < 0:
        page = 0
    p = pages[page]
    count = 0
    for role in p:
        view.add_item(Button(label=role.name, style=ButtonStyle.blurple, custom_id=f"self_role:role:{role.id}"))
        count += 1
    if len(pages) > 1:
        row = math.ceil(count / 5.0)
        view.add_item(Button(label=Translator.translate('prev_page', guild.id), style=ButtonStyle.grey, custom_id=f"self_role:page:{page - 1}", disabled=page == 0, row=row))
        view.add_item(Button(label=Translator.translate('next_page', guild.id), style=ButtonStyle.grey, custom_id=f"self_role:page:{page + 1}", disabled=page == len(pages), row=row))
