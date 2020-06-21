MASTER_CONFIG = dict()
SERVER_CONFIGS = dict()
MASTER_LOADED = False
PERSISTENT_LOADED = False
CONFIG_VERSION = 0
PERSISTENT = dict()
TEMPLATE = dict()


def save_master():
    global MASTER_CONFIG
    with open('config/master.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(MASTER_CONFIG, indent=4, skipkeys=True, sort_keys=True)))


# Ugly but this prevents import loop errors
def load_master():
    global MASTER_CONFIG, MASTER_LOADED
    try:
        with open('config/master.json', 'r') as jsonfile:
            MASTER_CONFIG = json.load(jsonfile)
            if "Serveradmin" in MASTER_CONFIG["COGS"]:
                MASTER_CONFIG["COGS"].remove("Serveradmin")
                MASTER_CONFIG["COGS"].append("ServerAdmin")
                save_master()
            MASTER_LOADED = True
    except FileNotFoundError:
        GearbotLogging.error("Unable to load config, running with defaults.")
    except Exception as e:
        GearbotLogging.error("Failed to parse configuration.")
        print(e)
        raise e


def get_master_var(key, default=None):
    global MASTER_CONFIG, MASTER_LOADED
    if not MASTER_LOADED:
        load_master()
    if not key in MASTER_CONFIG.keys():
        MASTER_CONFIG[key] = default
        save_master()
    return MASTER_CONFIG[key]


import json
import os

from discord.ext import commands

from Util import GearbotLogging, Utils, Features


def initial_migration(config):
    config["LOG_CHANNELS"] = dict()
    config["FUTURE_LOGS"] = False
    config["TIMESTAMPS"] = True

    keys = {
        "MINOR_LOGS": ["EDIT_LOGS", "NAME_CHANGES", "ROLE_CHANGES", "CENSOR_LOGS", "COMMAND_EXECUTED"],
        "JOIN_LOGS": ["JOIN_LOGS"],
        "MOD_LOGS": ["MOD_ACTIONS"],
    }

    for key, settings in keys.items():
        cid = config[key]
        if cid is not 0:
            found = False
            for channel, info in config["LOG_CHANNELS"].items():
                if cid == channel:
                    info.extend(settings)
                    found = True
            if not found:
                config["LOG_CHANNELS"][cid] = settings
        del config[key]
        for setting in settings:
            if setting not in config or not config[setting]:
                config[setting] = cid != 0
    for channel, info in config["LOG_CHANNELS"].items():
        log_all = all(all(t in info for t in types) for types in keys.values())
        if log_all:
            info.append("FUTURE_LOGS")
        config["FUTURE_LOGS"] = log_all


def v2(config):
    config["CENSOR_MESSAGES"] = len(config["INVITE_WHITELIST"]) > 0
    config["WORD_BLACKLIST"] = []
    config["MAX_MENTIONS"] = 0
    config["EMBED_EDIT_LOGS"] = True


def v3(config):
    for v in ["JOIN_LOGS", "MOD_ACTIONS", "NAME_CHANGES", "ROLE_CHANGES", "COMMAND_EXECUTED"]:
        del config[v]
    config["DM_ON_WARN"] = False
    for cid, info in config["LOG_CHANNELS"].items():
        if "CENSOR_LOGS" in info:
            info.remove("CENSOR_LOGS")
            info.append("CENSORED_MESSAGES")


def v4(config):
    if "CENSOR_LOGS" in config.keys():
        del config["CENSOR_LOGS"]
    for cid, info in config["LOG_CHANNELS"].items():
        if "FUTURE_LOGS" in info:
            info.append("ROLE_CHANGES")
            info.append("CHANNEL_CHANGES")
            info.append("VOICE_CHANGES")
            info.append("VOICE_CHANGES_DETAILED")


def v5(config):
    config["ROLE_WHITELIST"] = True
    config["ROLE_LIST"] = []
    if "Basic" in config["PERM_OVERRIDES"] and "role" in config["PERM_OVERRIDES"]:
        config["PERM_OVERRIDES"]["self_role"] = config["PERM_OVERRIDES"]["role"]
        del config["PERM_OVERRIDES"]["role"]


def v6(config):
    config["IGNORED_CHANNELS_CHANGES"] = []
    config["IGNORED_CHANNELS_OTHER"] = []


def v7(config):
    config["RAID_DETECTION"] = False
    config["RAID_TIME_LIMIT"] = 0
    config["RAID_TRIGGER_AMOUNT"] = 0
    config["RAID_CHANNEL"] = 0
    config[
        "RAID_MESSAGE"] = "<:gearDND:528335386238255106> RAID DETECTED, CALLING REINFORCEMENTS! <:gearDND:528335386238255106>"
    config["TIMEZONE"] = "Europe/Brussels"


def v8(config):
    for k in ["RAID_DETECTION", "RAID_TIME_LIMIT", "RAID_TRIGGER_AMOUNT", "RAID_CHANNEL"]:
        if k in config:
            del config[k]
    config["RAID_HANDLING"] = {
        "ENABLED": False,
        "SHIELDS": [],
        "INVITE": "",
        "NEXT_ID": 0
    }
    add_logging(config, "RAID_LOGS")


def v9(config):
    for k in ["cat", "dog", "jumbo"]:
        overrides = config["PERM_OVERRIDES"]
        if "Basic" in overrides:
            b = overrides["Basic"]["commands"]
            if k in b:
                if "Fun" not in overrides:
                    overrides["Fun"] = {
                        "commands": {},
                        "people": [],
                        "required": -1
                    }
                overrides["Fun"]["commands"][k] = dict(b[k])
                del b[k]


def v10(config):
    config["ANTI_SPAM"] = {
        "ENABLED": False,
        "EXEMPT_ROLES": [],
        "EXEMPT_USERS": [],
        "BUCKETS": []
    }
    if config["MAX_MENTIONS"] > 0:
        config["ANTI_SPAM"]["ENABLED"] = True
        config["ANTI_SPAM"]["BUCKETS"] = [
            {
                "TYPE": "max_mentions",
                "SIZE": {
                    "COUNT": config["MAX_MENTIONS"],
                    "PERIOD": 5
                },
                "PUNISHMENT": {
                    "TYPE": "ban"
                }
            }
        ]
        del config["MAX_MENTIONS"]


def v11(config):
    for cid, info in config["LOG_CHANNELS"].items():
        if "MOD_ACTIONS" in info:
            info.append("SPAM_VIOLATION")


def v12(config):
    config["NEW_USER_THRESHOLD"] = 86400


def v13(config):
    # fix antispam configs
    nuke_keys(config["ANTI_SPAM"], "CLEAN", "MAX_DUPLICATES", "MAX_MENTIONS", "MAX_MESSAGES", "MAX_NEWLINES",
              "PUNISHMENT",
              "PUNISHMENT_DURATION")
    if "BUCKETS" not in config["ANTI_SPAM"]:
        config["ANTI_SPAM"] = []

    # cleanup old junk
    nuke_keys(config, "DEV_ROLE", "FUTURE_LOGS")

    # restructuring
    move_keys(config, "GENERAL", "LANG", "PERM_DENIED_MESSAGE", "PREFIX", "TIMESTAMPS", "NEW_USER_THRESHOLD",
              "TIMEZONE")
    move_keys(config, "ROLES", "ADMIN_ROLES", "MOD_ROLES", "SELF_ROLES", "TRUSTED_ROLES", "ROLE_LIST", "ROLE_WHITELIST",
              "MUTE_ROLE")

    move_keys(config, "MESSAGE_LOGS", "IGNORED_CHANNELS_CHANGES", "IGNORED_CHANNELS_OTHER", "IGNORED_USERS")
    config["MESSAGE_LOGS"]["ENABLED"] = config["EDIT_LOGS"]
    del config["EDIT_LOGS"]
    config["MESSAGE_LOGS"]["EMBED"] = config["EMBED_EDIT_LOGS"]
    del config["EMBED_EDIT_LOGS"]

    move_keys(config, "CENSORING", "WORD_BLACKLIST", "INVITE_WHITELIST")
    config["CENSORING"]["ENABLED"] = config["CENSOR_MESSAGES"]
    del config["CENSOR_MESSAGES"]

    move_keys(config, "INFRACTIONS", "DM_ON_WARN")


def v14(config):
    if len(config["ANTI_SPAM"]) is 0:
        config["ANTI_SPAM"] = {
            "ENABLED": False,
            "BUCKETS": [],
            "EXEMPT_ROLES": [],
            "EXEMPT_USERS": []
        }


def v15(config):
    add_logging(config, 'CONFIG_CHANGES')


def v16(config):
    config["DASH_SECURITY"] = {
        "ACCESS": 2,
        "INFRACTION": 2,
        "VIEW_CONFIG": 2,
        "ALTER_CONFIG": 3
    }
    config["PERMISSIONS"] = {
        "LVL4_ROLES": [],
        "LVL4_USERS": [],
        "ADMIN_USERS": [],
        "MOD_USERS": [],
        "TRUSTED_USERS": []
    }
    for s in ["ADMIN", "MOD", "TRUSTED"]:
        key = f'{s}_ROLES'
        config["PERMISSIONS"][key] = config["ROLES"][key]
        del config["ROLES"][key]


def v17(config):
    config["CENSORING"]["ALLOW_TRUSTED_BYPASS"] = False


def v18(config):
    new = dict()
    for cid, logging_keys in config["LOG_CHANNELS"].items():
        new[cid] = {
            'CATEGORIES': logging_keys,
            'DISABLED_KEYS': []
        }
    config["LOG_CHANNELS"] = new


def v19(config):
    cat_map = {
        "EDIT_LOGS": "MESSAGE_LOGS",
        "JOIN_LOGS": "TRAVEL_LOGS",
        "COMMAND_EXECUTED": "MISC"
    }
    for cid, logging_keys in config["LOG_CHANNELS"].items():
        new_cats = set()
        for cat in logging_keys["CATEGORIES"]:
            if cat in cat_map:
                new_cats.add(cat_map[cat])
            else:
                new_cats.add(cat)
        logging_keys["CATEGORIES"] = [*new_cats]


def v20(config):
    config["SERVER_LINKS"] = []


def v21(config):
    config["CENSORING"]["TOKEN_BLACKLIST"] = config["CENSORING"]["WORD_BLACKLIST"]
    config["CENSORING"]["WORD_BLACKLIST"] = []

def v22(config):
    if "Serveradmin" in config["PERM_OVERRIDES"]:
        config["PERM_OVERRIDES"]["ServerAdmin"] =config["PERM_OVERRIDES"]["Serveradmin"]
        del config["PERM_OVERRIDES"]["Serveradmin"]

def v23(config):
    config["CENSORING"]["DOMAIN_WHITELIST"] = False
    config["CENSORING"]["DOMAIN_LIST"] = []

def v24(config):
    config["CENSORING"]["WORD_CENSORLIST"] = config["CENSORING"]["WORD_BLACKLIST"]
    del config["CENSORING"]["WORD_BLACKLIST"]
    config["CENSORING"]["TOKEN_CENSORLIST"] = config["CENSORING"]["TOKEN_BLACKLIST"]
    del config["CENSORING"]["TOKEN_BLACKLIST"]
    config["CENSORING"]["ALLOWED_INVITE_LIST"] = config["CENSORING"]["INVITE_WHITELIST"]
    del config["CENSORING"]["INVITE_WHITELIST"]
    config["CENSORING"]["DOMAIN_LIST_ALLOWED"] = config["CENSORING"]["DOMAIN_WHITELIST"]
    del config["CENSORING"]["DOMAIN_WHITELIST"]
    config["CENSORING"]["ROLE_LIST_MODE"] = config["ROLES"]["ROLE_WHITELIST"]
    del config["ROLES"]["ROLE_WHITELIST"]


def add_logging(config, *args):
    for cid, info in config["LOG_CHANNELS"].items():
        if "FUTURE_LOGS" in info:
            info.extend(args)


def nuke_keys(config, *keys):
    for key in keys:
        if key in config:
            del config[key]


def move_keys(config, section, *keys):
    if section not in config:
        config[section] = dict()
    for key in keys:
        if key in config:
            config[section][key] = config[key]
            del config[key]

# migrators for the configs, do NOT increase the version here, this is done by the migration loop
MIGRATORS = [initial_migration, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15, v16, v17, v18, v19, v20, v21, v22, v23, v24]

BOT = None


async def initialize(bot: commands.Bot):
    global CONFIG_VERSION, BOT, TEMPLATE
    BOT = bot
    TEMPLATE = Utils.fetch_from_disk("config/template")
    CONFIG_VERSION = TEMPLATE["VERSION"]
    GearbotLogging.info(f"Current template config version: {CONFIG_VERSION}")
    # GearbotLogging.info(f"Loading configurations for {len(bot.guilds)} guilds.")
    # for guild in bot.guilds:
    #     GearbotLogging.info(f"Loading info for {guild.name} ({guild.id}).")
    #     load_config(guild.id)
    #     validate_config(guild.id)


def load_config(guild):
    global SERVER_CONFIGS
    config = Utils.fetch_from_disk(f'config/{guild}')
    if "VERSION" not in config and len(config) < 15:
        GearbotLogging.info(f"The config for {guild} is to old to migrate, resetting")
        config = dict()
    else:
        if "VERSION" not in config:
            config["VERSION"] = 0
        SERVER_CONFIGS[guild] = update_config(guild, config)
    if len(config) is 0:
        GearbotLogging.info(f"No config available for {guild}, creating a blank one.")
        SERVER_CONFIGS[guild] = Utils.fetch_from_disk("config/template")
        save(guild)
    Features.check_server(guild)


def validate_config(guild_id):
    guild = BOT.get_guild(guild_id)
    # no guild means we're not there anymore, ignore it
    if guild is None:
        return
    for key in ["ADMIN_ROLES", "MOD_ROLES", "TRUSTED_ROLES"]:
        checklist(guild.id, key, guild.get_role)


def checklist(guid, key, getter):
    changed = False
    tr = list()
    cl = get_var(guid, "PERMISSIONS", key)
    for c in cl:
        if getter(c) is None:
            tr.append(c)
            changed = True
    for r in tr:
        cl.remove(r)
    if changed:
        save(guid)


def update_config(guild, config):
    while config["VERSION"] < CONFIG_VERSION:
        v = config["VERSION"]
        GearbotLogging.info(f"Upgrading config version from version {v} to {v + 1}")
        d = f"config/backups/v{v}"
        if not os.path.isdir(d):
            os.makedirs(d)
        Utils.save_to_disk(f"{d}/{guild}", config)
        MIGRATORS[config["VERSION"]](config)
        config["VERSION"] += 1
        Utils.save_to_disk(f"config/{guild}", config)

    return config


def get_var(id, section, key=None, default=None):
    if id is None:
        raise ValueError("Where is this coming from?")
    if not id in SERVER_CONFIGS.keys():
        GearbotLogging.info(f"Config entry requested before config was loaded for guild {id}, loading config for it")
        load_config(id)
    s = SERVER_CONFIGS[id].get(section, {})
    if key is not None:
        s = s.get(key, default)
    return s


def set_var(id, cat, key, value):
    SERVER_CONFIGS[id].get(cat, dict())[key] = value
    save(id)
    Features.check_server(id)


def set_cat(id, cat, value):
    SERVER_CONFIGS[id][cat] = value
    save(id)
    Features.check_server(id)


def save(id):
    global SERVER_CONFIGS
    with open(f'config/{id}.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(SERVER_CONFIGS[id], indent=4, skipkeys=True, sort_keys=True)))
    Features.check_server(id)


def load_persistent():
    global PERSISTENT_LOADED, PERSISTENT
    PERSISTENT = Utils.fetch_from_disk('persistent')
    PERSISTENT_LOADED = True


def get_persistent_var(key, default):
    if not PERSISTENT_LOADED:
        load_persistent()
    return PERSISTENT[key] if key in PERSISTENT else default


def set_persistent_var(key, value):
    PERSISTENT[key] = value
    Utils.save_to_disk("persistent", PERSISTENT)
