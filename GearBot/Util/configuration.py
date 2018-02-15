import json
import logging

import copy
import discord
from discord.ext import commands

import Variables
from Util import GearbotLogging

MASTER_CONFIG = dict()
SERVER_CONFIGS = dict()

CONFIG_TEMPLATE = {
    "dummy": "info"
}


def loadGlobalConfig():
    global MASTER_CONFIG
    try:
        with open('config/master.json', 'r') as jsonfile:
            MASTER_CONFIG = json.load(jsonfile)
    except FileNotFoundError:
        logging.error("Unable to load config, running with defaults")
    except Exception as e:
        logging.error("Failed to parse configuration")
        print(e)
        raise e
    # Database.initialize()


async def onReady(bot:commands.Bot):
    GearbotLogging.info(f"Loading configurations for {len(bot.guilds)} guilds")
    for guild in bot.guilds:
        GearbotLogging.info(f"Loading info for {guild.name} ({guild.id})")
        await loadConfig(guild)


async def loadConfig(guild:discord.Guild):
    global SERVER_CONFIGS
    try:
        with open(f'config/{guild.id}.json', 'r') as jsonfile:
            SERVER_CONFIGS[guild.id] = json.load(jsonfile)
    except FileNotFoundError:
        logging.info(f"No config available for {guild.name} ({guild.id}, creating blank one")
        SERVER_CONFIGS[guild.id] = copy.deepcopy(CONFIG_TEMPLATE)
        saveConfig(guild.id)

def saveConfig(id):
    global SERVER_CONFIGS
    with open(f'config/{id}.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(SERVER_CONFIGS[id], indent=4, skipkeys=True, sort_keys=True)))

def getMasterConfigVar(key, default=None) :
    global MASTER_CONFIG
    if not key in MASTER_CONFIG.keys():
        MASTER_CONFIG[key] = default
        saveMasterConfig()
    return MASTER_CONFIG[key]


def saveMasterConfig():
    global MASTER_CONFIG
    with open('config/master.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(MASTER_CONFIG, indent=4, skipkeys=True, sort_keys=True)))
