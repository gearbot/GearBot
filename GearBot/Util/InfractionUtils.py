from datetime import datetime

from Util import Pages, Utils
from database.DatabaseConnector import Infraction

cache = dict()


def add_infraction(guild_id, user_id, mod_id, type, reason, end=None, active=True):
    Infraction.create(guild_id=guild_id, user_id=user_id, mod_id=mod_id, type=type, reason=reason,
                      start=datetime.now(), end=end, active=active)
    if f"{guild_id}_{user_id}" in cache.keys():
        del cache[f"{guild_id}_{user_id}"]
    if f"{guild_id}_{None}" in cache.keys():
        del cache[f"{guild_id}_{None}"]


async def get_infraction_pages(guild_id, query, amount):
    if f"{guild_id}_{query}" not in cache.keys():
        if query is None:
            infs = Infraction.select().where(Infraction.guild_id == guild_id).order_by(Infraction.id.desc()).limit(amount)
        else:
            infs = Infraction.select().where((Infraction.guild_id == guild_id) & (
                    (Infraction.user_id == query) | (Infraction.mod_id == query))).order_by(Infraction.id.desc()).limit(amount)

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
            longest_type = max(longest_type, len(inf.type))
        for inf in infs:
            user = await Utils.username(inf.user_id, clean=False)
            mod = await Utils.username(inf.mod_id, clean=False)
            out += f"{Utils.pad(str(inf.id), longest_id)} | {Utils.pad(user, longest_user)} | {Utils.pad(mod, longest_mod)} | {inf.start} | {Utils.pad(inf.type, longest_type)} | {inf.reason}\n"
        prefix = f"{Utils.pad('id', longest_id)} | {Utils.pad('user', longest_user-1)}| {Utils.pad('moderator', longest_mod-1)}| timestamp           | {Utils.pad('type', longest_type)} | reason"
        prefix = f"```md\n{prefix}\n{'-' * len(prefix)}\n"
        pages = Pages.paginate(out, prefix=prefix, suffix="```")
        cache[f"{guild_id}_{query}"] = pages
    if len(cache.keys()) > 20:
        del cache[list(cache.keys())[0]]
    return cache[f"{guild_id}_{query}"]
