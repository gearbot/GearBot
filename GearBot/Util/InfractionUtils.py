from datetime import datetime

from peewee import fn

from Bot import GearBot
from Util import Pages, Utils, Translator
from database.DatabaseConnector import Infraction

bot:GearBot = None

def initialize(gearbot):
    global bot
    bot = gearbot

def add_infraction(guild_id, user_id, mod_id, type, reason, end=None, active=True):
    Infraction.create(guild_id=guild_id, user_id=user_id, mod_id=mod_id, type=type, reason=reason,
                      start=datetime.now(), end=end, active=active)
    bot.loop.create_task(clear_cache(guild_id))

async def clear_cache(guild_id):
    if bot.redis_pool is None:
        return
    keys = set()
    async for key in bot.redis_pool.iscan(match=f"{guild_id}*"):
        keys.add(key)
    if len(keys) > 0:
        if None in keys:
            keys.remove(None)
        await bot.redis_pool.unlink(*keys)


async def get_infraction_pages(guild_id, query, amount, fields):
    key = f"{guild_id}_{query}"
    if query is not None:
        key += f"_{'_'.join(fields)}"
    # check if we got it cached
    redis_pool = bot.redis_pool
    cache = redis_pool is not None
    length = await redis_pool.llen(key) if cache else 0
    if length is 0:
        if query == "":
            infs = Infraction.select().where(Infraction.guild_id == guild_id).order_by(Infraction.id.desc()).limit(50)
        else:
            infs = Infraction.select().where((Infraction.guild_id == guild_id) & (
                    ("[user]" in fields and isinstance(query, int) and Infraction.user_id == query ) |
                    ("[mod]" in fields and isinstance(query, int) and Infraction.mod_id == query) |
                     ("[reason]" in fields and fn.lower(Infraction.reason).contains(str(query).lower())))).order_by(Infraction.id.desc()).limit(50)

        out = ""
        longest_user = 0
        longest_mod = 9
        longest_type = 4
        longest_id = len(str(infs[0].id)) if len(infs) > 0 else 2
        for inf in infs:
            user = await Utils.username(inf.user_id, clean=False)
            longest_user = max(longest_user, len(user))
            mod = await Utils.username(inf.mod_id, clean=False)
            longest_mod = max(longest_mod, len(mod))
            longest_type = max(longest_type, len(Translator.translate(inf.type, guild_id)))
        if cache:
            pipe = redis_pool.pipeline()
        count = 0
        for inf in infs:
            user = await Utils.username(inf.user_id, clean=False)
            mod = await Utils.username(inf.mod_id, clean=False)
            i = f"{Utils.pad(str(inf.id), longest_id)} | {Utils.pad(user, longest_user)} | {Utils.pad(mod,longest_mod)} | {inf.start} | {Utils.pad(Translator.translate(inf.type.lower(), guild_id), longest_type)} | {inf.reason}\n"
            if count < amount:
                out += i
                count +=1
            if cache:
                pipe.rpush(key, i)
        prefix = f"{Utils.pad('id', longest_id)} | {Utils.pad('user', longest_user - 1)}| {Utils.pad('moderator',longest_mod - 1)}| timestamp           | {Utils.pad('type', longest_type)} | reason"
        prefix = f"```md\n{prefix}\n{'-' * len(prefix)}\n"
        if cache:
            pipe.lpush(key, prefix)
            pipe.expire(key, 5*60)
            bot.loop.create_task(pipe.execute())
        pages = Pages.paginate(out, prefix=prefix, suffix="```")
        return pages
    else:
        parts = await bot.redis_pool.lrange(key, 0, amount)
        prefix = parts[0]
        return Pages.paginate("".join(parts[1:]), prefix=prefix, suffix="```")
