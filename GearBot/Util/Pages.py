import discord

from Util import Utils, Emoji, Translator

page_handlers = dict()

known_messages = dict()


def on_ready(bot):
    load_from_disc()


def register(type, init, update, sender_only=False):
    page_handlers[type] = {
        "init": init,
        "update": update,
        "sender_only": sender_only
    }


def unregister(type_handler):
    if type_handler in page_handlers.keys():
        del page_handlers[type_handler]


async def create_new(type, ctx, **kwargs):
    text, embed, has_pages, emoji = await page_handlers[type]["init"](ctx, **kwargs)
    message: discord.Message = await ctx.channel.send(text, embed=embed)
    if has_pages or len(emoji) > 0:
        data = {
            "type": type,
            "page": 0,
            "trigger": ctx.message.id,
            "sender": ctx.author.id
        }
        for k, v in kwargs.items():
            data[k] = v
        known_messages[str(message.id)] = data
        try:
            if has_pages: await message.add_reaction(Emoji.get_emoji('LEFT'))
            for e in emoji: await message.add_reaction(e)
            if has_pages: await message.add_reaction(Emoji.get_emoji('RIGHT'))
        except discord.Forbidden:
            await ctx.send(
                f"{Emoji.get_chat_emoji('WARNING')} {Translator.translate('paginator_missing_perms', ctx, prev=Emoji.get_chat_emoji('LEFT'), next=Emoji.get_chat_emoji('RIGHT'))} {Emoji.get_chat_emoji('WARNING')}")

    if len(known_messages.keys()) > 500:
        del known_messages[list(known_messages.keys())[0]]

    save_to_disc()


async def update(bot, message, action, user):
    message_id = str(message.id)
    if message_id in known_messages.keys():
        type = known_messages[message_id]["type"]
        if type in page_handlers.keys():
            data = known_messages[message_id]
            if data["sender"] == user or page_handlers[type]["sender_only"] is False:
                page_num = data["page"]
                try:
                    trigger_message = await message.channel.get_message(data["trigger"])
                except discord.NotFound:
                    trigger_message = None
                ctx = await bot.get_context(trigger_message) if trigger_message is not None else None
                text, embed, page = await page_handlers[type]["update"](ctx, message, page_num, action, data)
                await message.edit(content=text, embed=embed)
                known_messages[message_id]["page"] = page
                save_to_disc()
                return True
    return False


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
                    name = f"{base_name} ({i+1}/{len(parts)})"
                    if page_count + len(name) + len(part) > 3000:
                        real_pages.append(page_fields)
                        page_fields = dict()
                        page_count = 0
                    page_fields[name] = part
                    page_count += len(name) + len(part)
        real_pages.append(page_fields)
    return real_pages


def save_to_disc():
    Utils.saveToDisk("known_messages", known_messages)


def load_from_disc():
    global known_messages
    known_messages = Utils.fetch_from_disk("known_messages")
