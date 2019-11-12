from collections import OrderedDict

from Util import Permissioncheckers, Configuration, server_info


class DASH_PERMS:
    ACCESS = (1 << 0)
    VIEW_INFRACTIONS = (1 << 1)
    VIEW_CONFIG = (1 << 2)
    ALTER_CONFIG = (1 << 3)


def get_user_guilds(bot, user_id):
    info = dict()
    for guild in bot.guilds:
        guid = guild.id
        permission = get_guild_perms(guild.get_member(user_id))
        if permission > 0:
            info[str(guid)] = {
                "id": str(guid),
                "name": guild.name,
                "permissions": permission,
                "icon": guild.icon
            }

    return OrderedDict(sorted(info.items()))


def get_guild_perms(member):
    if member is None:
        return 0

    mappings = {
        "ACCESS": DASH_PERMS.ACCESS,
        "INFRACTION": DASH_PERMS.VIEW_INFRACTIONS,
        "VIEW_CONFIG": DASH_PERMS.VIEW_CONFIG,
        "ALTER_CONFIG": DASH_PERMS.ALTER_CONFIG
    }

    permission = 0
    user_lvl = Permissioncheckers.user_lvl(member)
    for k, v in mappings.items():
        if user_lvl >= Configuration.get_var(member.guild.id, "DASH_SECURITY", k):
            permission |= v

    return permission


def assemble_guild_info(bot, member):
    return {
        "guild_info": server_info.server_info_raw(bot, member.guild),
        "user_perms": {
            "user_dash_perms": get_guild_perms(member),
            "user_level": Permissioncheckers.user_lvl(member)
        }
    }
