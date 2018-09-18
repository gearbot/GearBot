import json

from discord.ext import commands

from Util import GearbotLogging, Utils

MASTER_CONFIG = dict()
SERVER_CONFIGS = dict()
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
                    for setting in settings:
                        info.append(setting)
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

    return config



# migrators for the configs, do NOT increase the version here, this is done by the migration loop
MIGRATORS = [initial_migration]

async def on_ready(bot: commands.Bot):
    global CONFIG_VERSION
    CONFIG_VERSION = Utils.fetch_from_disk("config/template")["VERSION"]
    GearbotLogging.info(f"Current template config version: {CONFIG_VERSION}")
    GearbotLogging.info(f"Loading configurations for {len(bot.guilds)} guilds.")
    for guild in bot.guilds:
        GearbotLogging.info(f"Loading info for {guild.name} ({guild.id}).")
        load_config(guild.id)


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
        SERVER_CONFIGS[guild] = update_config(config)
    if len(config) is 0:
        GearbotLogging.info(f"No config available for {guild}, creating a blank one.")
        SERVER_CONFIGS[guild] = Utils.fetch_from_disk("config/template")
        save(guild)

def update_config(config):
    v = config["VERSION"]
    while config["VERSION"] < CONFIG_VERSION:
        GearbotLogging.info(f"Upgrading config version from version {v} to {v+1}")
        config = MIGRATORS[config["VERSION"]](config)
        config["VERSION"] += 1

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


def save(id):
    global SERVER_CONFIGS
    with open(f'config/{id}.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(SERVER_CONFIGS[id], indent=4, skipkeys=True, sort_keys=True)))


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
