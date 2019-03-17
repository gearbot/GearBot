from datetime import datetime

from peewee import fn

from Bot import GearBot
from Util import Pages, Utils, Translator, GearbotLogging, Emoji, ReactionManager
from Util.Matchers import ID_MATCHER
from database.DatabaseConnector import Infraction

bot:GearBot = None

def initialize(gearbot):
    global bot
    bot = gearbot

def add_infraction(guild_id, user_id, mod_id, type, reason, end=None, active=True):
    i = Infraction.create(guild_id=guild_id, user_id=user_id, mod_id=mod_id, type=type, reason=reason,
                      start=datetime.now(), end=end, active=active)
    bot.loop.create_task(clear_cache(guild_id))
    return i

async def clear_cache(guild_id):
    if bot.redis_pool is not None:
        todo = await inf_cleaner(guild_id, reset_cache=True)
        for view in todo:
            bot.loop.create_task(ReactionManager.on_reaction(bot, view[0], view[1], 0, None))

async def fetch_infraction_pages(guild_id, query, amount, fields, requested):
    key = get_key(guild_id, query, fields, amount)
    if query == "":
        infs = Infraction.select().where(Infraction.guild_id == guild_id).order_by(Infraction.id.desc()).limit(50)
    else:
        infs = Infraction.select().where((Infraction.guild_id == guild_id) & (
                ("[user]" in fields and isinstance(query, int) and Infraction.user_id == query) |
                ("[mod]" in fields and isinstance(query, int) and Infraction.mod_id == query) |
                ("[reason]" in fields and fn.lower(Infraction.reason).contains(str(query).lower())))).order_by(
            Infraction.id.desc()).limit(amount)
    longest_type = 4
    longest_id = len(str(infs[0].id)) if len(infs) > 0 else len(Translator.translate('id', guild_id))
    longest_timestamp = max(len(Translator.translate('timestamp', guild_id)), 19)
    types = dict()
    for inf in infs:
        t = inf.type.lower()
        longest_type = max(longest_type, len(Translator.translate(t, guild_id)))
        if t not in types:
            types[t] = 1
        else:
            types[t] += 1
    header = ", ".join(Translator.translate(f"{k}s", guild_id, count=v) for k, v in types.items())
    out = "\n".join(f"{Utils.pad(str(inf.id), longest_id)} | <@{inf.user_id}> | <@{inf.mod_id}> | {inf.start} | {Utils.pad(Translator.translate(inf.type.lower(), guild_id), longest_type)} | {Utils.trim_message(inf.reason, 1550)}" for inf in infs)
    pages = Pages.paginate(out, max_chars=(1600 - len(header)))
    placeholder = Translator.translate("inf_search_compiling", guild_id)
    if bot.redis_pool is not None:
        GearbotLogging.info(f"Pushing placeholders for {key}")
        pipe = bot.redis_pool.pipeline()
        for page in pages:
            pipe.lpush(key, placeholder)
        await pipe.execute()
    bot.loop.create_task(update_pages(guild_id, query, fields, amount, pages, requested, longest_id, longest_type, longest_timestamp, header))
    return len(pages)


async def update_pages(guild_id, query, fields, amount, pages, start, longest_id, longest_type, longest_timestamp, header):
    key = get_key(guild_id, query, fields, amount)
    order = [start]
    lower = start - 1
    upper = start + 1
    GearbotLogging.info(f"Determining page order for {key}")
    while len(order) < len(pages):
        if upper == len(pages):
            upper = 0
        order.append(upper)
        upper+=1
        if len(order) == len(pages):
            break
        if lower == -1:
            lower = len(pages)-1
        order.append(lower)
        lower -= 1
    GearbotLogging.info(f"Updating pages for {key}, ordering: {order}")
    for number in order:
        longest_name = max(len(Translator.translate('moderator', guild_id)), len(Translator.translate('user', guild_id)))
        page = pages[number]
        found = set(ID_MATCHER.findall(page))
        for uid in found:
            name = await Utils.username(int(uid), clean=False)
            longest_name = max(longest_name, len(name))
        for uid in found:
            name = Utils.pad(await Utils.username(int(uid), clean=False), longest_name)
            page = page.replace(f"<@{uid}>", name).replace(f"<@!{uid}>", name)
        page = f"{header}```md\n{get_header(longest_id, longest_name, longest_type, longest_timestamp, guild_id)}\n{page}```"
        GearbotLogging.info(f"Finished assembling page {number} for key {key}")
        await bot.redis_pool.lset(key, number, page)
        pages[number] = page
        GearbotLogging.info(f"Pushed page {number} for key {key} to redis")
        bot.dispatch("page_assembled", {
            "key": key,
            "page_num": number,
            "page": page
        })
    GearbotLogging.info(f"All pages assembled for key {key}, setting expiry to 10 minutes")
    bot.dispatch("all_pages_assembled", {
        "key": key,
        "pages": pages
    })
    await bot.redis_pool.expire(key, 60 * 60)


def get_header(longest_id, longest_user, longest_type, longest_timestamp, guild_id):
    text = f"{Utils.pad(Translator.translate('id', guild_id), longest_id)} | {Utils.pad(Translator.translate('user', guild_id), longest_user )} | {Utils.pad(Translator.translate('moderator', guild_id),longest_user)} | {Utils.pad(Translator.translate('timestamp', guild_id), longest_timestamp)} | {Utils.pad(Translator.translate('type', guild_id), longest_type)} | {Translator.translate('reason', guild_id)}\n"
    return text + ("-" * len(text))


def get_key(guild_id, query, fields, amount):
    key = f"infractions:{guild_id}_{query}"
    if query is not None:
        key += f"{'_'.join(fields)}"
    key += f"_{amount}"
    return key

async def inf_update(message, query, fields, amount, page_num):
    guild_id = message.channel.guild.id
    key = get_key(guild_id, query, fields, amount)
    # do we have pages?
    count = await bot.redis_pool.llen(key)
    if count is 0:
        count = await fetch_infraction_pages(guild_id, query, amount, fields, page_num)
        if page_num >= count:
            page_num = 0
        elif page_num < 0:
            page_num = count-1
        page = (await bot.wait_for("page_assembled", check=lambda l: l["key"] == key and l["page_num"] == page_num))["page"]
    else:
        if page_num >= count:
            page_num = 0
        elif page_num < 0:
            page_num = count-1
        page = await bot.redis_pool.lindex(key, page_num)
    name = await Utils.username(query) if isinstance(query, int) else bot.get_guild(guild_id).name
    await message.edit(content=f"{Emoji.get_chat_emoji('SEARCH')} {Translator.translate('inf_search_header', message.channel.guild.id, name=name, page_num=page_num + 1, pages=count)}\n{page}")
    if count > 1:
        left = Emoji.get_emoji('LEFT')
        if not any(left == r.emoji and r.me for r in message.reactions):
            await message.add_reaction(Emoji.get_emoji('LEFT'))
            await message.add_reaction(Emoji.get_emoji('RIGHT'))

    parts = {
        "page_num": page_num,
        "cache_key": key
    }
    if len(fields) == 3:
        parts["fields"] = "-".join(fields)
    if query is not None:
        parts["query"] = query
    if amount != 100:
        parts["amount"] = 100
    return parts


async def inf_cleaner(guild_id, reset_cache=False):
    pipeline = bot.redis_pool.pipeline()
    key = f"inf_track:{guild_id}"
    reactors = await bot.redis_pool.smembers(key)
    for reactor in reactors:
        pipeline.hget(f"reactor:{reactor}", "channel_id")
        pipeline.hget(f"reactor:{reactor}", "cache_key")
    bits = await pipeline.execute()
    out = list()
    pipeline = bot.redis_pool.pipeline()
    for i in range(len(reactors)):
        target = i * 2
        if bits[target] is None:
            pipeline.srem(key, reactors[i])
        else:
            out.append((reactors[i], int(bits[target])))
        if reset_cache and bits[target + 1] is not None:
            pipeline.unlink(bits[target + 1])
    bot.loop.create_task(pipeline.execute())
    return out
