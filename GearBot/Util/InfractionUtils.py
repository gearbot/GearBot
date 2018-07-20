from datetime import datetime

from Util import Pages, Utils
from database.DatabaseConnector import Infraction

cache = dict()

def add_infraction(guild_id, user_id, mod_id, type, reason):
    Infraction.create(guild_id=guild_id, user_id=user_id, mod_id=mod_id, type=type, reason=reason, timestamp=datetime.now())
    if f"{guild_id}_{user_id}" in cache.keys():
        del cache[f"{guild_id}_{user_id}"]


async def get_infraction_pages(guild_id, query):
    if f"{guild_id}_{query}" not in cache.keys():
        infs = Infraction.select().where((Infraction.guild_id == guild_id) & (
                    (Infraction.user_id == query) | (Infraction.mod_id == query))).order_by(Infraction.id.desc())

        out = ""
        longest_user = 0
        longest_mod = 0
        for inf in infs:
            user = await Utils.username(inf.user_id)
            longest_user = max(longest_user, len(user))
            mod = await Utils.username(inf.mod_id)
            longest_mod = max(longest_mod, len(mod))
            out += f"{inf.id} | {user} | {mod} | {inf.timestamp} | {inf.type} | {inf.reason}\n"
        prefix = f"id| user {' ' * (longest_user-4)}| moderator {' ' * (longest_mod- 9)}| timestamp           | type | reason"
        prefix = f"```\n{prefix}\n{'-' * len(prefix)}\n"
        pages = Pages.paginate(out, prefix=prefix, suffix="```")
        cache[f"{guild_id}_{query}"] = pages
    if len(cache.keys()) > 20:
        del cache[list(cache.keys())[0]]
    return cache[f"{guild_id}_{query}"]