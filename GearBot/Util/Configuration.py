import copy
import json

from discord.ext import commands

from Util import GearbotLogging

MASTER_CONFIG = dict()
SERVER_CONFIGS = dict()
master_loaded = False

CONFIG_TEMPLATE = {
    "PREFIX": "!",
    "MINOR_LOGS": 0,
    "JOIN_LOGS": 0,
    "MOD_LOGS": 0,
    "MUTE_ROLE": 0,
    "DEV_ROLE": 0,
    "SELF_ROLES": [],
    "IGNORED_USERS": [],
    "INVITE_WHITELIST": [],
    "ADMIN_ROLES": [],
    "MOD_ROLES": [],
    "TRUSTED_ROLES": [],
    "COG_OVERRIDES": dict(),
    "COMMAND_OVERRIDES": dict(),
    "LANG": "en_US"

}


async def onReady(bot:commands.Bot):
    GearbotLogging.info(f"Loading configurations for {len(bot.guilds)} guilds.")
    for guild in bot.guilds:
        GearbotLogging.info(f"Loading info for {guild.name} ({guild.id}).")
        loadConfig(guild.id)


def loadGlobalConfig():
    global MASTER_CONFIG, master_loaded
    try:
        with open('config/master.json', 'r') as jsonfile:
            MASTER_CONFIG = json.load(jsonfile)
            master_loaded = True
    except FileNotFoundError:
        GearbotLogging.error("Unable to load config, running with defaults.")
    except Exception as e:
        GearbotLogging.error("Failed to parse configuration.")
        print(e)
        raise e


def loadConfig(guild):
    global SERVER_CONFIGS
    try:
        with open(f'config/{guild}.json', 'r') as jsonfile:
            config = json.load(jsonfile)
            for key in CONFIG_TEMPLATE:
                if key not in config:
                    if CONFIG_TEMPLATE[key] == []:
                        config[key] = []
                    else:
                        config[key] = CONFIG_TEMPLATE[key]
            if "MOD_ROLE_ID" in config:
                config["MOD_ROLES"].append(config["MOD_ROLE_ID"])
                del config["MOD_ROLE_ID"]
            if "ADMIN_ROLE_ID" in config:
                config["ADMIN_ROLES"].append(config["ADMIN_ROLE_ID"])
                del config["ADMIN_ROLE_ID"]
            SERVER_CONFIGS[guild] = config
    except FileNotFoundError:
        GearbotLogging.info(f"No config available for {guild}, creating a blank one.")
        SERVER_CONFIGS[guild] = copy.deepcopy(CONFIG_TEMPLATE)
        saveConfig(guild)

def getConfigVar(id, key):
    if not id in SERVER_CONFIGS.keys():
        GearbotLogging.info(f"Config entry requested before config was loaded for guild {id}, loading config for it")
        loadConfig(id)
    return SERVER_CONFIGS[id][key]

def getConfigVarChannel(id, key, bot:commands.Bot):
    return bot.get_channel(getConfigVar(id, key))

def setConfigVar(id, key, value):
    SERVER_CONFIGS[id][key] = value
    saveConfig(id)

def saveConfig(id):
    global SERVER_CONFIGS
    with open(f'config/{id}.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(SERVER_CONFIGS[id], indent=4, skipkeys=True, sort_keys=True)))

def getMasterConfigVar(key, default=None) :
    global MASTER_CONFIG, master_loaded
    if not master_loaded:
        loadGlobalConfig()
    if not key in MASTER_CONFIG.keys():
        MASTER_CONFIG[key] = default
        saveMasterConfig()
    return MASTER_CONFIG[key]


def saveMasterConfig():
    global MASTER_CONFIG
    with open('config/master.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(MASTER_CONFIG, indent=4, skipkeys=True, sort_keys=True)))