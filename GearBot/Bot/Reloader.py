from Bot import TheRealGearBot
from Cogs import BaseCog
from Util import Configuration, GearbotLogging, Emoji, Pages, Utils, Translator, Converters, Permissioncheckers, \
    VersionInfo, Confirmation, HelpGenerator, InfractionUtils, Archive, DocUtils, JumboGenerator, MessageUtils, Enums, \
    Matchers, Questions, Selfroles, ReactionManager, server_info, DashConfig, Update, DashUtils, Actions
from Util.RaidHandling import RaidActions, RaidShield
from database import DatabaseConnector, DBUtils

components = [
    Configuration,
    DatabaseConnector,
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
    JumboGenerator,
    MessageUtils,
    TheRealGearBot,
    Converters,
    Enums,
    Matchers,
    Questions,
    RaidActions,
    RaidShield,
    ReactionManager,
    Selfroles,
    DBUtils,
    server_info,
    DashConfig,
    Update,
    BaseCog,
    DashUtils,
    Actions
]
