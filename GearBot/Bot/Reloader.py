from Bot import TheRealGearBot
from Util import Configuration, GearbotLogging, Emoji, Pages, Utils, Translator, Converters, Permissioncheckers, \
    VersionInfo, Confirmation, HelpGenerator, InfractionUtils, Archive, DocUtils, JumboGenerator, MessageUtils, Enums, \
    Matchers
from database import DatabaseConnector

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
    JumboGenerator,
    MessageUtils,
    TheRealGearBot,
    Enums,
    Matchers
]