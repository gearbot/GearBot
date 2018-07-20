from Util import *
from database import DatabaseConnector
from . import Configuration, Converters, GearbotLogging, Pages, Permissioncheckers, Utils, VersionInfo, Confirmation, HelpGenerator, Emoji, InfractionUtils

components = [
    Configuration,
    Converters,
    GearbotLogging,
    Permissioncheckers,
    Utils,
    VersionInfo,
    DatabaseConnector,
    Emoji,
    Confirmation,
    HelpGenerator,
    Pages,
    InfractionUtils
]

async def reload(bot):
    import importlib
    for c in components:
        importlib.reload(c)
    prepDatabase(bot)
    await readyBot(bot)

async def readyBot(bot):
    await Configuration.onReady(bot)
    Emoji.on_ready(bot)
    Confirmation.on_ready(bot)
    Pages.on_ready(bot)
    Utils.on_ready(bot)
    bot.data = {
        "forced_exits": [],
        "unbans": []
    }
    await GearbotLogging.onReady(bot, Configuration.getMasterConfigVar("BOT_LOG_CHANNEL"))

def prepDatabase(bot):
    GearbotLogging.info("Connecting to the database.")
    DatabaseConnector.init()
    bot.database_connection = DatabaseConnector.connection
    GearbotLogging.info("Database connection established.")