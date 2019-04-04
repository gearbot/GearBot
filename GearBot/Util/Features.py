from Util import Configuration

LOG_MAP = dict()


def check_server(guild_id):
    enabled = set()
    for cid, info in Configuration.get_var(guild_id, "LOG_CHANNELS").items():
        enabled.update(info)
    LOG_MAP[guild_id] = enabled


def is_logged(guild, feature):
    return guild in LOG_MAP and feature in LOG_MAP[guild]


requires_logging = {
    "CENSOR_MESSAGES": "CENSORED_MESSAGES",
    "EDIT_LOGS": "EDIT_LOGS"
}


def can_enable(guild, feature):
    return feature not in requires_logging or is_logged(guild, requires_logging[feature])

def is_enabled(guild, feature):
    return Configuration.get_var(guild, feature)