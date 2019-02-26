import time
from datetime import datetime

from peewee import fn

from Bot import GearBot
from Util import Pages, Utils, Translator, GearbotLogging
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
    if bot.redis_pool is None:
        return
    keys = set()
    async for key in bot.redis_pool.iscan(match=f"{guild_id}*"):
        keys.add(key)
    if None in keys:
        keys.remove(None)
    if len(keys) > 0:
        await bot.redis_pool.unlink(*keys)

async def get_infraction_pages(key, guild_id, query, amount, fields, requested, message):
    start = time.perf_counter()
    if query == "":
        infs = Infraction.select().where(Infraction.guild_id == guild_id).order_by(Infraction.id.desc()).limit(50)
    else:
        infs = Infraction.select().where((Infraction.guild_id == guild_id) & (
                ("[user]" in fields and isinstance(query, int) and Infraction.user_id == query) |
                ("[mod]" in fields and isinstance(query, int) and Infraction.mod_id == query) |
                ("[reason]" in fields and fn.lower(Infraction.reason).contains(str(query).lower())))).order_by(
            Infraction.id.desc()).limit(amount)
    duration = time.perf_counter() - start
    GearbotLogging.info(f"Fetched {len(infs)} infractions for key {key} in {duration}ns, processing")
    longest_type = 4
    longest_id = len(str(infs[0].id)) if len(infs) > 0 else len(Translator.translate('id', message.guild.id))
    longest_timestamp = max(len(Translator.translate('timestamp', guild_id)), 19)
    types = dict()
    start = time.perf_counter()
    for inf in infs:
        t = inf.type.lower()
        longest_type = max(longest_type, len(Translator.translate(t, guild_id)))
        if t not in types:
            types[t] = 1
        else:
            types[t] += 1
    header = ", ".join(Translator.translate(f"{k}s", guild_id, count=v) for k, v in types.items())
    out = "\n".join(f"{Utils.pad(str(inf.id), longest_id)} | <@{inf.user_id}> | <@{inf.mod_id}> | {inf.start} | {Utils.pad(Translator.translate(inf.type.lower(), guild_id), longest_type)} | {inf.reason}" for inf in infs)
    pages = Pages.paginate(out, max_chars=1700 - len(header))
    GearbotLogging.info(f"Processed {len(infs)} infractions for {key} in {duration}")
    placeholder = Translator.translate("inf_search_compiling", guild_id)
    bot.loop.create_task(cache_and_start(placeholder, key, pages, requested, message, longest_id, longest_type, longest_timestamp, header))
    return [placeholder for page in pages]

async def cache_and_start(placeholder, key, pages, requested, message, longest_id, longest_type, longest_timestamp, header):
    if bot.redis_pool is not None:
        GearbotLogging.info(f"Pusing placeholders for {key} and expiring keys")
        pipe = bot.redis_pool.pipeline()
        for page in pages:
            await pipe.lpush(key, placeholder)
        await pipe.execute()

    await update_pages(key, pages, requested, message, longest_id, longest_type, longest_timestamp, header)


async def get_page(guild_id, query, amount, fields, requested, message):
    key = f"{guild_id}_{query}_{amount}"
    if query is not None:
        key += f"_{'_'.join(fields)}"
    GearbotLogging.info(f'Infraction page {requested} requested for key {key}')
    # check if we got it cached
    cache = bot.redis_pool is not None
    length = await bot.redis_pool.llen(key) if cache else 0
    if length == 0:
        GearbotLogging.info(f"Infraction key {key} wasn't cached, generating, ...")
        return (await get_infraction_pages(key, guild_id, query, amount, fields, requested, message))[requested]
    else:
        GearbotLogging.info(f"Infraction key {key} found, fetching page {requested} from redis")
        data = await bot.redis_pool.lindex(key, requested)
        GearbotLogging.info(f"Sucessfully fetched page {requested} for key {key} from redis")
        return data


async def update_pages(key, pages, start, message, longest_id, longest_type, longest_timestamp, header):
    order = [start]
    lower = start - 1
    upper = start + 1
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
        longest_name = max(len(Translator.translate('moderator', message.guild.id)), len(Translator.translate('user', message.guild.id)))
        page = pages[number]
        found = set(ID_MATCHER.findall(page))
        for uid in found:
            name = await Utils.username(int(uid), clean=False)
            longest_name = max(longest_name, len(name))
        for uid in found:
            name = Utils.pad(await Utils.username(int(uid), clean=False), longest_name)
            page = page.replace(f"<@{uid}>", name).replace(f"<@!{uid}>", name)
        page = f"{header}```md\n{get_header(longest_id, longest_name, longest_type, longest_timestamp, message.guild.id)}\n{page}```"
        GearbotLogging.info(f"Finished assembling page {number} for key {key}, page data:\n{page}")
        await bot.redis_pool.lset(key, number, page)
        GearbotLogging.info(f"Pushed page {number} for key {key} to redis")
        info = Pages.known_messages[str(message.id)]
        if info["page"] == number:
            await Pages.update(bot, message, "UPDATE", None)

    GearbotLogging.info(f"All pages assembled for key {key}, setting expiry to 10 minutes")
    await bot.redis_pool.expire(key, 10 * 60)


def get_header(longest_id, longest_user, longest_type, longest_timestamp, guild_id):
    text = f"{Utils.pad(Translator.translate('id', guild_id), longest_id)} | {Utils.pad(Translator.translate('user', guild_id), longest_user )} | {Utils.pad(Translator.translate('moderator', guild_id),longest_user)} | {Utils.pad(Translator.translate('timestamp', guild_id), longest_timestamp)} | {Utils.pad(Translator.translate('type', guild_id), longest_type)} | {Translator.translate('reason', guild_id)}\n"
    return text + ("-" * len(text))

async def get_page_count(guild_id, query, amount, fields, requested, message):
    key = f"{guild_id}_{query}"
    if query is not None:
        key += f"_{'_'.join(fields)}"
    # check if we got it cached
    cache = bot.redis_pool is not None
    length = await bot.redis_pool.llen(key) if cache else 0
    if length is not 0:
        return length
    else:
        return len(await get_infraction_pages(key, guild_id, query, amount, fields, requested, message))