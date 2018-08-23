from database import DatabaseConnector
from . import Configuration, Converters, GearbotLogging, Pages, Permissioncheckers, Utils, VersionInfo, Confirmation, HelpGenerator, Emoji, InfractionUtils, Archive, Translator, DocUtils, GlobalHandlers

components = [
    Configuration,
    DatabaseConnector,
    Converters,
    GearbotLogging,
    Permissioncheckers,
    Utils,
    VersionInfo,
    Emoji,
    Confirmation,
    HelpGenerator,
    Pages,
    InfractionUtils,
    Archive,
    Translator,
    DocUtils,
    GlobalHandlers
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
    Translator.on_ready(bot)
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