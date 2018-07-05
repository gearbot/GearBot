from Util import *
from database import DatabaseConnector
from . import Configuration, Converters, GearbotLogging, Pages, Permissioncheckers, Utils, VersionInfo, Confirmation

components = [
    Configuration,
    Converters,
    GearbotLogging,
    Pages,
    Permissioncheckers,
    Utils,
    VersionInfo,
    DatabaseConnector,
    Confirmation
]

async def reload(bot):
    for c in components:
        importlib.reload(c)
    prepDatabase(bot)
    await readyBot(bot)

async def readyBot(bot):
    await Configuration.onReady(bot)
    Confirmation.on_ready(bot)
    Pages.on_ready(bot)
    await GearbotLogging.onReady(bot, Configuration.getMasterConfigVar("BOT_LOG_CHANNEL"))

def prepDatabase(bot):
    GearbotLogging.info("Connecting to the database")
    DatabaseConnector.init()
    bot.database_connection = DatabaseConnector.connection
    GearbotLogging.info("Database connection established")