from Util import Configuration

LOG_MAP = dict()


async def check_server(guild_id):
    enabled = set()
    for cid, info in (await Configuration.get_var(guild_id, "LOG_CHANNELS")).items():
        enabled.update(info["CATEGORIES"])
    LOG_MAP[guild_id] = enabled


def is_logged(guild, feature):
    return guild in LOG_MAP and feature in LOG_MAP[guild]


requires_logging = {
    "CENSOR_MESSAGES": "CENSORING",
    "EDIT_LOGS": "MESSAGE_LOGS"
}


def can_enable(guild, feature):
    return feature not in requires_logging or is_logged(guild, requires_logging[feature])