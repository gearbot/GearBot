import discord
from discord import NotFound, Forbidden

from Util import Emoji, ReactionManager, MessageUtils

page_handlers = dict()


def register(type, init, update):
    page_handlers[type] = {
        "init": init,
        "update": update,
    }


def unregister(type_handler):
    if type_handler in page_handlers.keys():
        del page_handlers[type_handler]


async def create_new(bot, type, ctx, **kwargs):
    text, embed, has_pages = await page_handlers[type]["init"](ctx, **kwargs)
    message: discord.Message = await ctx.channel.send(text, embed=embed)
    if has_pages:
        await ReactionManager.register(bot, message.id, message.channel.id, "paged", subtype=type, **kwargs)
        try:
            if has_pages: await message.add_reaction(Emoji.get_emoji('LEFT'))
            if has_pages: await message.add_reaction(Emoji.get_emoji('RIGHT'))
        except discord.Forbidden:
            await MessageUtils.send_to(ctx, 'WARNING', 'paginator_missing_perms', prev=Emoji.get_chat_emoji('LEFT'),
                                       next=Emoji.get_chat_emoji('RIGHT'))
        except discord.NotFound:
            await MessageUtils.send_to(ctx, 'WARNING', 'fix_censor')


async def update(bot, message, action, user, **kwargs):
    subtype = kwargs.get("subtype", "")
    if subtype in page_handlers.keys():
        if "sender" not in kwargs or int(user) == int(kwargs["sender"]):
            page_num = kwargs.get("page", 0)
            ctx = None
            if "trigger" in kwargs:
                try:
                    trigger_message = await message.channel.fetch_message(kwargs["trigger"])
                    ctx = await bot.get_context(trigger_message)
                except (NotFound, Forbidden):
                    pass
            text, embed, info = await page_handlers[subtype]["update"](ctx, message, int(page_num), action, kwargs)
            try:
                await message.edit(content=text, embed=embed)
            except (NotFound, Forbidden):
                pass  # weird shit but happens sometimes
            return info
        return


def basic_pages(pages, page_num, action):
    if action == "PREV":
        page_num -= 1
    elif action == "NEXT":
        page_num += 1
    if page_num < 0:
        page_num = len(pages) - 1
    if page_num >= len(pages):
        page_num = 0
    page = pages[page_num]
    return page, page_num


def paginate(input, max_lines=20, max_chars=1900, prefix="", suffix=""):
    max_chars -= len(prefix) + len(suffix)
    lines = str(input).splitlines(keepends=True)
    pages = []
    page = ""
    count = 0
    for line in lines:
        if len(page) + len(line) > max_chars or count == max_lines:
            if page == "":
                # single 2k line, split smaller
                words = line.split(" ")
                for word in words:
                    if len(page) + len(word) > max_chars:
                        pages.append(f"{prefix}{page}{suffix}")
                        page = f"{word} "
                    else:
                        page += f"{word} "
            else:
                pages.append(f"{prefix}{page}{suffix}")
                page = line
                count = 1
        else:
            page += line
        count += 1
    pages.append(f"{prefix}{page}{suffix}")
    return pages


def paginate_fields(input):
    pages = []
    for page in input:
        page_fields = dict()
        for name, content in page.items():
            page_fields[name] = paginate(content, max_chars=1024)
        pages.append(page_fields)
    real_pages = []
    for page in pages:
        page_count = 0
        page_fields = dict()
        for name, parts in page.items():
            base_name = name
            if len(parts) is 1:
                if page_count + len(name) + len(parts[0]) > 4000:
                    real_pages.append(page_fields)
                    page_fields = dict()
                    page_count = 0
                page_fields[name] = parts[0]
                page_count += len(name) + len(parts[0])
            else:
                for i in range(len(parts)):
                    part = parts[i]
                    name = f"{base_name} ({i + 1}/{len(parts)})"
                    if page_count + len(name) + len(part) > 3000:
                        real_pages.append(page_fields)
                        page_fields = dict()
                        page_count = 0
                    page_fields[name] = part
                    page_count += len(name) + len(part)
        real_pages.append(page_fields)
    return real_pages
