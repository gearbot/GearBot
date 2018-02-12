import json
import logging

import Variables

GLOBAL_CONFIG = dict()


def loadGlobalConfig():
    global GLOBAL_CONFIG
    try:
        with open('config/config.json', 'r') as jsonfile:
            GLOBAL_CONFIG = json.load(jsonfile)
    except FileNotFoundError:
        logging.error("Unable to load config, running with defaults")
    except Exception as e:
        logging.error("Failed to parse configuration")
        print(e)
        raise e
    Variables.PREFIX = getConfigVar("PREFIX", "!")
    # Database.initialize()


def onReady():
    global GLOBAL_CONFIG
    Variables.MOD_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("MOD_LOG_CHANNEL", "0"))
    Variables.BOT_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("BOT_LOG_CHANNEL", "0"))
    Variables.ANNOUNCEMENTS_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("ANNOUNCEMENTS_CHANNEL", "0"))
    Variables.TESTING_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("TESTING_CHANNEL", "0"))
    Variables.GENERAL_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("GENERAL_CHANNEL", "0"))
    Variables.MINOR_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("MINOR_LOG_CHANNEL", "0"))
    Variables.JOIN_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("JOIN_LOG_CHANNEL", "0"))


def getConfigVar(key, default=None) :
    global GLOBAL_CONFIG
    if not key in GLOBAL_CONFIG.keys():
        GLOBAL_CONFIG[key] = default
        saveConfig()
    return GLOBAL_CONFIG[key]

def setConfigVar(key, value):
    global GLOBAL_CONFIG
    GLOBAL_CONFIG[key] = value
    saveConfig()


def saveConfig():
    global GLOBAL_CONFIG
    with open('config.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(GLOBAL_CONFIG, indent=4, skipkeys=True, sort_keys=True)))
