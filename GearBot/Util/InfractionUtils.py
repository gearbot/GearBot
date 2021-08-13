import asyncio
import json
import re
import time
import datetime

from aioredis import ReplyError
from discord import NotFound
from tortoise.query_utils import Q

from Bot import GearBot
from Util import Pages, Utils, Translator, GearbotLogging, Emoji, ReactionManager
from database.DatabaseConnector import Infraction

bot:GearBot = None

def initialize(gearbot):
    global bot
    bot = gearbot

async def add_infraction(guild_id, user_id, mod_id, type, reason, end=None, active=True):
    i = await Infraction.create(guild_id=guild_id, user_id=user_id, mod_id=mod_id, type=type, reason=reason,
                      start=datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).timestamp(), end=end, active=active)
    clear_cache(guild_id)
    return i

cleaners = dict()

def clear_cache(guild_id):
    if guild_id in cleaners:
        cleaners[guild_id].cancel()
    cleaners[guild_id] = bot.loop.create_task(cleaner(guild_id))



async def cleaner(guild_id):
    count = 0
    todo = await inf_cleaner(guild_id, reset_cache=True)
    if guild_id in cleaners:
        del cleaners[guild_id]

async def fetch_infraction_pages(guild_id, query, amount, fields, requested, globaly=False):
    key = get_key(guild_id, query, fields, amount, globaly)
    if query == "":
        infs = await Infraction.filter(guild_id = guild_id).order_by("-id").limit(50)
    else:
        subfilters = []
        if "[user]" in fields and isinstance(query, int):
            subfilters.append(Q(user_id=query))
        if "[mod]" in fields and isinstance(query, int):
            subfilters.append(Q(mod_id=query))
        if "[reason]" in fields:
            subfilters.append(Q(reason__icontains=str(query)))

        if globaly:
            infs = await Infraction.filter(Q(Q(*subfilters, join_type="OR"), join_type="AND")).order_by("-id").limit(int(amount))
        else:
            infs = await Infraction.filter(Q(Q(*subfilters, join_type="OR"), guild_id=guild_id, join_type="AND")).order_by("-id").limit(int(amount))
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
    name = await Utils.username(query) if isinstance(query, int) else await Utils.clean(bot.get_guild(guild_id).name)
    title = f"{Emoji.get_chat_emoji('SEARCH')} {Translator.translate('inf_search_header', guild_id, name=name, page_num=100, pages=100)}\n```md\n\n```"
    page_header = get_header(longest_id, 37, longest_type, longest_timestamp, guild_id)
    mcount = 2000 - len(header) - len(page_header) - len(title)
    gid = f' {guild_id} |' if globaly else ''
    out = "\n".join(f"{Utils.pad(str(inf.id), longest_id)} |{gid} <@{Utils.pad(str(inf.user_id), 37)}> | <@{Utils.pad(str(inf.mod_id), 37)}> | {datetime.datetime.fromtimestamp(inf.start)} | {Utils.pad(Translator.translate(inf.type.lower(), guild_id), longest_type)} | {Utils.trim_message(inf.reason, 1000)}" for inf in infs)
    pages = Pages.paginate(out, max_chars=mcount)
    if bot.redis_pool is not None:
        GearbotLogging.debug(f"Pushing placeholders for {key}")
        pipe = bot.redis_pool.pipeline()
        pipe.unlink(key)
        for page in pages:
            pipe.lpush(key, "---NO PAGE YET---")
        await pipe.execute()
    bot.loop.create_task(update_pages(guild_id, query, fields, amount, pages, requested, longest_id, longest_type, longest_timestamp, header, globaly=globaly))
    return len(pages)

ID_MATCHER = re.compile("<@!?([0-9]+\s*)>")

async def update_pages(guild_id, query, fields, amount, pages, start, longest_id, longest_type, longest_timestamp, header, globaly=False):
    key = get_key(guild_id, query, fields, amount, globaly=globaly)
    count = len(pages)
    if start >= count:
        start = 0
    elif start < 0:
        start = count - 1
    order = [start]
    lower = start - 1
    upper = start + 1
    GearbotLogging.debug(f"Determining page order for {key}")
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
    GearbotLogging.debug(f"Updating pages for {key}, ordering: {order}")
    for number in order:
        longest_name = max(len(Translator.translate('moderator', guild_id)), len(Translator.translate('user', guild_id)))
        page = pages[number]
        found = set(ID_MATCHER.findall(page))
        for uid in found:
            name = await Utils.username(int(uid.strip()), clean=False)
            longest_name = max(longest_name, len(name))
        for uid in found:
            name = Utils.pad(await Utils.username(int(uid.strip()), clean=False), longest_name)
            page = page.replace(f"<@{uid}>", name).replace(f"<@!{uid}>", name)
        page = f"{header}```md\n{get_header(longest_id, longest_name, longest_type, longest_timestamp, guild_id)}\n{page}```"
        GearbotLogging.debug(f"Finished assembling page {number} for key {key}")
        try:

            await bot.redis_pool.lset(key, number, page)
        except ReplyError:
            return # key expired while we where working on it
        pages[number] = page
        GearbotLogging.debug(f"Pushed page {number} for key {key} to redis")
        bot.dispatch("page_assembled", {
            "key": key,
            "page_num": number,
            "page": page
        })
    GearbotLogging.debug(f"All pages assembled for key {key}, setting expiry to 60 minutes")
    bot.dispatch("all_pages_assembled", {
        "key": key,
        "pages": pages
    })
    await bot.redis_pool.expire(key, 60 * 60)


def get_header(longest_id, longest_user, longest_type, longest_timestamp, guild_id, globaly=False):
    text = f"{Utils.pad(Translator.translate('id', guild_id), longest_id)}{Utils.pad(' |Guild Id', 20) if globaly else ''} | {Utils.pad(Translator.translate('user', guild_id), longest_user )} | {Utils.pad(Translator.translate('moderator', guild_id),longest_user)} | {Utils.pad(Translator.translate('timestamp', guild_id), longest_timestamp)} | {Utils.pad(Translator.translate('type', guild_id), longest_type)} | {Translator.translate('reason', guild_id)}\n"
    return text + ("-" * len(text))


def get_key(guild_id, query, fields, amount, globaly=False):
    start = "global_infractions" if globaly else "infractions"
    key = f"{start}:{guild_id}_{query}"
    if query is not None:
        key += f"{'_'.join(fields)}"
    key += f"_{amount}"
    return key

async def assemble_message(guild_id, page, query, page_num, count, globaly=False):
    name = await Utils.username(query) if isinstance(query, int) else await Utils.clean(bot.get_guild(guild_id).name) if not globaly else 'Global'
    return f"{Emoji.get_chat_emoji('SEARCH')} {Translator.translate('inf_search_header', guild_id, name=name, page_num=page_num + 1, pages=count)}\n{page}"


async def inf_cleaner(guild_id, reset_cache=False):
    pipeline = bot.redis_pool.pipeline()
    key = f"inf_track:{guild_id}"
    reactors = await bot.redis_pool.smembers(key)
    for reactor in reactors:
        pipeline.get(f"inf_meta:{reactor}")
    bits = await pipeline.execute()
    out = list()
    pipeline = bot.redis_pool.pipeline()
    for i in range(len(reactors)):
        target = i
        if bits[target] is None:
            pipeline.srem(key, reactors[i])
        if reset_cache:
            data = json.loads(bits[target])
            pipeline.unlink(get_key(guild_id, data['query'], data['fields'].split(' '), data['amount']))
    await pipeline.execute()
    return out
