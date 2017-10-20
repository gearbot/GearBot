import json
import logging

import Variables
from Util import Database

CONFIG_VARIABLES = dict()


def loadconfig():
    global CONFIG_VARIABLES
    try:
        with open('config.json', 'r') as jsonfile:
            CONFIG_VARIABLES = json.load(jsonfile)
    except FileNotFoundError:
        logging.error("Unable to load config, running with defaults")
    except Exception as e:
        logging.error("Failed to parse configuration")
        print(e)
        raise e
    Variables.PREFIX = getConfigVar("PREFIX", "!")
    Database.initialize()

def onReady():
    global CONFIG_VARIABLES
    Variables.MOD_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("MOD_LOG_CHANNEL", "0"))
    Variables.BOT_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(getConfigVar("BOT_LOG_CHANNEL", "0"))

def getConfigVar(key, default=None) :
    global CONFIG_VARIABLES
    if not key in CONFIG_VARIABLES.keys():
        CONFIG_VARIABLES[key] = default
        saveConfig()
    return CONFIG_VARIABLES[key]

def saveConfig():
    global CONFIG_VARIABLES
    with open('config.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(CONFIG_VARIABLES, indent=4, skipkeys=True, sort_keys=True)))
