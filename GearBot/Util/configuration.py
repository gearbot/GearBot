import json
import Variables
from logging import DEBUG, INFO
import logging

def loadconfig():
    try:
        with open('config.json', 'r') as jsonfile:
            jsondata = json.load(jsonfile)
            Variables.CONFIG_SETTINGS = jsondata
            Variables.MOD_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(jsondata["MOD_LOG_CHANNEL"])
            Variables.BOT_LOG_CHANNEL = Variables.DISCORD_CLIENT.get_channel(jsondata["BOT_LOG_CHANNEL"])
            Variables.PREFIX = jsondata["PREFIX"]
    except FileNotFoundError:
        logging.error("Unable to load config, creating a fresh one and running on defaults. This will almost surely crash when trying to connect to the database")
        Variables.CONFIG_SETTINGS["PREFIX"] = "!"
        Variables.CONFIG_SETTINGS["BOT_LOG_CHANNEL"] = None
        Variables.CONFIG_SETTINGS["MOD_LOG_CHANNEL"] = None
        Variables.CONFIG_SETTINGS["DATABASE_USER"] = "username"
        Variables.CONFIG_SETTINGS["DATABASE_PASS"] = "password"
        Variables.CONFIG_SETTINGS["DATABASE_NAME"] = "database"
        saveConfig()
    except Exception as e:
        logging.error("Failed to parse configuration")
        print(e)
        raise e


def saveConfig():
    with open('config.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(Variables.CONFIG_SETTINGS, indent=4, skipkeys=True, sort_keys=True)))
