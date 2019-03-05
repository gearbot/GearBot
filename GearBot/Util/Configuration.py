import json
import os

from discord.ext import commands

from Util import GearbotLogging, Utils, Features

MASTER_CONFIG = dict()
SERVER_CONFIGS = dict()
PERSISTENT = dict()
MASTER_LOADED = False
CONFIG_VERSION = 0

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
    config["RAID_MESSAGE"] = "<:gearDND:528335386238255106> RAID DETECTED, CALLING REINFORCEMENTS! <:gearDND:528335386238255106>"
    config["TIMEZONE"] = "Europe/Brussels"

def v8(config):
    for k in ["RAID_DETECTION", "RAID_TIME_LIMIT", "RAID_TRIGGER_AMOUNT", "RAID_CHANNEL"]:
        del config[k]
    config["RAID_HANDLING"] = {
        "ENABLED": False,
        "HANDLERS": [],
        "INVITE": ""
    }

def add_logging(config, *args):
    for cid, info in config["LOG_CHANNELS"].items():
        if "FUTURE_LOGS" in info:
            info.extend(args)

# migrators for the configs, do NOT increase the version here, this is done by the migration loop
MIGRATORS = [initial_migration, v2, v3, v4, v5, v6, v7, v8]

async def initialize(bot: commands.Bot):
    global CONFIG_VERSION, PERSISTENT
    CONFIG_VERSION = Utils.fetch_from_disk("config/template")["VERSION"]
    PERSISTENT = Utils.fetch_from_disk("persistent")
    GearbotLogging.info(f"Current template config version: {CONFIG_VERSION}")
    GearbotLogging.info(f"Loading configurations for {len(bot.guilds)} guilds.")
    for guild in bot.guilds:
        GearbotLogging.info(f"Loading info for {guild.name} ({guild.id}).")
        load_config(guild.id)
        validate_config(guild)


def load_master():
    global MASTER_CONFIG, MASTER_LOADED
    try:
        with open('config/master.json', 'r') as jsonfile:
            MASTER_CONFIG = json.load(jsonfile)
            MASTER_LOADED = True
    except FileNotFoundError:
        GearbotLogging.error("Unable to load config, running with defaults.")
    except Exception as e:
        GearbotLogging.error("Failed to parse configuration.")
        print(e)
        raise e


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

def validate_config(guild):
    for key in ["ADMIN_ROLES", "MOD_ROLES", "SELF_ROLES", "TRUSTED_ROLES"]:
        checklist(guild.id, key, guild.get_channel)

def checklist(guid, key, getter):
    changed = False
    tr = list()
    cl = get_var(guid, key)
    for c in cl:
        if getter(c) is None:
            tr.append(c)
            changed = True
    for r in tr:
        cl.remove(r)
    if changed:
        set_var(guid, key, cl)



def update_config(guild, config):
    v = config["VERSION"]
    while config["VERSION"] < CONFIG_VERSION:
        GearbotLogging.info(f"Upgrading config version from version {v} to {v+1}")
        d = f"config/backups/v{v}"
        if not os.path.isdir(d):
            os.makedirs(d)
        Utils.saveToDisk(f"{d}/{guild}", config)
        MIGRATORS[config["VERSION"]](config)
        config["VERSION"] += 1
        Utils.saveToDisk(f"config/{guild}", config)

    return config


def get_var(id, key):
    if id is None:
        raise ValueError("Where is this coming from?")
    if not id in SERVER_CONFIGS.keys():
        GearbotLogging.info(f"Config entry requested before config was loaded for guild {id}, loading config for it")
        load_config(id)
    return SERVER_CONFIGS[id][key]


def set_var(id, key, value):
    SERVER_CONFIGS[id][key] = value
    save(id)
    Features.check_server(id)


def save(id):
    global SERVER_CONFIGS
    with open(f'config/{id}.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(SERVER_CONFIGS[id], indent=4, skipkeys=True, sort_keys=True)))
    Features.check_server(id)


def get_master_var(key, default=None):
    global MASTER_CONFIG, MASTER_LOADED
    if not MASTER_LOADED:
        load_master()
    if not key in MASTER_CONFIG.keys():
        MASTER_CONFIG[key] = default
        save_master()
    return MASTER_CONFIG[key]


def save_master():
    global MASTER_CONFIG
    with open('config/master.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(MASTER_CONFIG, indent=4, skipkeys=True, sort_keys=True)))

def get_persistent_var(key, default):
    return PERSISTENT[key] if key in PERSISTENT else default

def set_persistent_var(key,  value):
    PERSISTENT[key] = value
    Utils.saveToDisk("persistent", PERSISTENT)