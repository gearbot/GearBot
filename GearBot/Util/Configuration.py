from typing import NamedTuple, List, Dict
from enum import Enum
from pytz import timezone, UnknownTimeZoneError

MASTER_CONFIG = dict()
SERVER_CONFIGS = dict()
MASTER_LOADED = False
CONFIG_VERSION = 0


def validate_bool_value(value):
    if type(value) == bool:
        return True
    else:
        return False

def validate_string_value(value):
    if type(value) == str:
        if value != "":
            return True
    return False


class ConfigGeneral(NamedTuple):
    lang: str
    def validate_lang(value):
        if validate_string_value():
            if len(value) <= 25:
                return True
        return False

    perm_denied_message: bool
    def validate_perm_denied_message(value):
        return validate_bool_value(value)

    prefix: str
    def validate_prefix(value):
        if validate_string_value(value):
            if len(value) <= 10:
                    return True
        return False

    timestamps: bool
    def validate_timestamps(value):
        return validate_bool_value(value)

    new_user_threshold: int
    def validate_new_user_threshold(value):
        if type(value) == int:
            if value >= 0 and value <= (60 * 60 * 24 * 14):
                return True
        return False

    timezone: str
    def validate_timezone(value): 
        if validate_string_value(value):
            try:
                timezone(value)
                return True
            except UnknownTimeZoneError:
                return False
        return False


class ConfigRoles(NamedTuple):
    def validate_role(role_id):
        if type(role_id) == int:
            return True # TODO: See if role exists in guild
        else:
            return False
            
    admin_roles: List[int]
    mod_roles: List[int]
    self_roles: List[int]
    trusted_roles: List[int]
    role_list: List[int]

    role_whitelist: bool
    def validate_role_whitelist(value): 
        return validate_bool_value(value)

    mute_role: int
    def validate_mute_role(role_id): 
        return validate_role()


LogChannel = Dict[str, List[str]]
LogChannels = Dict[str, LogChannel]


class ConfigMessageLogs(NamedTuple):
    def validate_channel(channel_id):
        if type(channel_id) == int:
            if channel_id: # TODO: See if channel ID exists
                return True
        return False

    enabled: bool
    def validate_enabled(value): 
        return validate_bool_value(value)

    ignored_channels_changes: List[int]
    ignored_channels_other: List[int]
    ignored_users: List[int]

    embed: bool
    def validate_embed(value): 
        return validate_bool_value(value)


class ConfigCensoring(NamedTuple):
    enabled: bool
    def validate_enabled(value): 
        return validate_bool_value(value)

    word_blacklist: List[str]
    invite_whitelist: List[str]


class ConfigInfractions(NamedTuple):
    dm_on_warn: bool
    def validate_dm_on_warn(value): 
        return validate_bool_value(value)


RaidShield = None  # Dict[] TODO


class ConfigRaidHandling(NamedTuple):
    enabled: bool
    def validate_enabled(value):
        return validate_bool_value(value)

    handlers: List[RaidShield]  # TODO: Need a example to make a type sig

    invite: str
    def validate_invite(value): 
        return validate_string_value(value)


class PunishmentTypes(Enum):
    warn: "warn"
    kick: "kick"
    ban: "ban"
    forced_ban: "forced_ban"
    mute: "mute"


class SpamTypes(Enum):
    duplicates: "duplicates"
    messages: "max_messages"
    newlines: "max_newlines"
    mentions: "max_mentions"


class SpamSize(NamedTuple):
    count: int
    period: int


class SpamBucketParts(NamedTuple):
    spam_type: SpamTypes
    punishment: Dict[str, PunishmentTypes]  # May need tweaked
    size: SpamSize


SpamBucket = List[SpamBucketParts]


class ConfigAntiSpam(NamedTuple):
    clean: bool
    def validate_clean(value):
        return validate_bool_value(value)

    enabled: bool
    def validate_enabled(value): 
        return validate_bool_value(value)

    exempt_roles: List[int]
    exempt_users: List[int]
    buckets: List[SpamBucket]


class ConfigTypes(NamedTuple):
    version: int
    general: ConfigGeneral
    roles: ConfigRoles
    log_channels: LogChannels
    message_logs: ConfigMessageLogs
    censoring: ConfigCensoring
    infrations: ConfigInfractions
    perm_overrides: None  # TODO: How to represent this reasonably
    raid_handling: ConfigRaidHandling
    anti_spam: ConfigAntiSpam


# Ugly but this prevents import loop errors
def load_master():
    global MASTER_CONFIG, MASTER_LOADED
    try:
        with open('config/master.json', 'r') as jsonfile:
            MASTER_CONFIG = json.load(jsonfile)
            MASTER_LOADED = True
    except FileNotFoundError:
        GearbotLogging.error("Unable to load config, running with defaults.")
    except Exception as e:
        GearbotLogging.error("Failed to parse configuration.")
        print(e)
        raise e


def get_master_var(key, default=None):
    global MASTER_CONFIG, MASTER_LOADED
    if not MASTER_LOADED:
        load_master()
    if not key in MASTER_CONFIG.keys():
        MASTER_CONFIG[key] = default
        save_master()
    return MASTER_CONFIG[key]


import json
import os

from discord.ext import commands

from Util import GearbotLogging, Utils, Features


def initial_migration(config):
    config["LOG_CHANNELS"] = dict()
    config["FUTURE_LOGS"] = False
    config["TIMESTAMPS"] = True

    keys = {
        "MINOR_LOGS": ["EDIT_LOGS", "NAME_CHANGES", "ROLE_CHANGES", "CENSOR_LOGS", "COMMAND_EXECUTED"],
        "JOIN_LOGS": ["JOIN_LOGS"],
        "MOD_LOGS": ["MOD_ACTIONS"],
    }

    for key, settings in keys.items():
        cid = config[key]
        if cid is not 0:
            found = False
            for channel, info in config["LOG_CHANNELS"].items():
                if cid == channel:
                    info.extend(settings)
                    found = True
            if not found:
                config["LOG_CHANNELS"][cid] = settings
        del config[key]
        for setting in settings:
            if setting not in config or not config[setting]:
                config[setting] = cid != 0
    for channel, info in config["LOG_CHANNELS"].items():
        log_all = all(all(t in info for t in types) for types in keys.values())
        if log_all:
            info.append("FUTURE_LOGS")
        config["FUTURE_LOGS"] = log_all


def v2(config):
    config["CENSOR_MESSAGES"] = len(config["INVITE_WHITELIST"]) > 0
    config["WORD_BLACKLIST"] = []
    config["MAX_MENTIONS"] = 0
    config["EMBED_EDIT_LOGS"] = True


def v3(config):
    for v in ["JOIN_LOGS", "MOD_ACTIONS", "NAME_CHANGES", "ROLE_CHANGES", "COMMAND_EXECUTED"]:
        del config[v]
    config["DM_ON_WARN"] = False
    for cid, info in config["LOG_CHANNELS"].items():
        if "CENSOR_LOGS" in info:
            info.remove("CENSOR_LOGS")
            info.append("CENSORED_MESSAGES")


def v4(config):
    if "CENSOR_LOGS" in config.keys():
        del config["CENSOR_LOGS"]
    for cid, info in config["LOG_CHANNELS"].items():
        if "FUTURE_LOGS" in info:
            info.append("ROLE_CHANGES")
            info.append("CHANNEL_CHANGES")
            info.append("VOICE_CHANGES")
            info.append("VOICE_CHANGES_DETAILED")


def v5(config):
    config["ROLE_WHITELIST"] = True
    config["ROLE_LIST"] = []
    if "Basic" in config["PERM_OVERRIDES"] and "role" in config["PERM_OVERRIDES"]:
        config["PERM_OVERRIDES"]["self_role"] = config["PERM_OVERRIDES"]["role"]
        del config["PERM_OVERRIDES"]["role"]


def v6(config):
    config["IGNORED_CHANNELS_CHANGES"] = []
    config["IGNORED_CHANNELS_OTHER"] = []


def v7(config):
    config["RAID_DETECTION"] = False
    config["RAID_TIME_LIMIT"] = 0
    config["RAID_TRIGGER_AMOUNT"] = 0
    config["RAID_CHANNEL"] = 0
    config[
        "RAID_MESSAGE"] = "<:gearDND:528335386238255106> RAID DETECTED, CALLING REINFORCEMENTS! <:gearDND:528335386238255106>"
    config["TIMEZONE"] = "Europe/Brussels"


def v8(config):
    for k in ["RAID_DETECTION", "RAID_TIME_LIMIT", "RAID_TRIGGER_AMOUNT", "RAID_CHANNEL"]:
        if k in config:
            del config[k]
    config["RAID_HANDLING"] = {
        "ENABLED": False,
        "SHIELDS": [],
        "INVITE": "",
        "NEXT_ID": 0
    }
    add_logging(config, "RAID_LOGS")


def v9(config):
    for k in ["cat", "dog", "jumbo"]:
        overrides = config["PERM_OVERRIDES"]
        if "Basic" in overrides:
            b = overrides["Basic"]["commands"]
            if k in b:
                if "Fun" not in overrides:
                    overrides["Fun"] = {
                        "commands": {},
                        "people": [],
                        "required": -1
                    }
                overrides["Fun"]["commands"][k] = dict(b[k])
                del b[k]


def v10(config):
    config["ANTI_SPAM"] = {
        "ENABLED": False,
        "EXEMPT_ROLES": [],
        "EXEMPT_USERS": [],
        "BUCKETS": []
    }
    if config["MAX_MENTIONS"] > 0:
        config["ANTI_SPAM"]["ENABLED"] = True
        config["ANTI_SPAM"]["BUCKETS"] = [
            {
                "TYPE": "max_mentions",
                "SIZE": {
                    "COUNT": config["MAX_MENTIONS"],
                    "PERIOD": 5
                },
                "PUNISHMENT": {
                    "TYPE": "ban"
                }
            }
        ]
        del config["MAX_MENTIONS"]


def v11(config):
    for cid, info in config["LOG_CHANNELS"].items():
        if "MOD_ACTIONS" in info:
            info.append("SPAM_VIOLATION")


def v12(config):
    config["NEW_USER_THRESHOLD"] = 86400


def v13(config):
    # fix antispam configs
    nuke_keys(config["ANTI_SPAM"], "CLEAN", "MAX_DUPLICATES", "MAX_MENTIONS", "MAX_MESSAGES", "MAX_NEWLINES",
              "PUNISHMENT",
              "PUNISHMENT_DURATION")
    if "BUCKETS" not in config["ANTI_SPAM"]:
        config["ANTI_SPAM"] = []

    # cleanup old junk
    nuke_keys(config, "DEV_ROLE", "FUTURE_LOGS")

    # restructuring
    move_keys(config, "GENERAL", "LANG", "PERM_DENIED_MESSAGE", "PREFIX", "TIMESTAMPS", "NEW_USER_THRESHOLD",
              "TIMEZONE")
    move_keys(config, "ROLES", "ADMIN_ROLES", "MOD_ROLES", "SELF_ROLES", "TRUSTED_ROLES", "ROLE_LIST", "ROLE_WHITELIST",
              "MUTE_ROLE")

    move_keys(config, "MESSAGE_LOGS", "IGNORED_CHANNELS_CHANGES", "IGNORED_CHANNELS_OTHER", "IGNORED_USERS")
    config["MESSAGE_LOGS"]["ENABLED"] = config["EDIT_LOGS"]
    del config["EDIT_LOGS"]
    config["MESSAGE_LOGS"]["EMBED"] = config["EMBED_EDIT_LOGS"]
    del config["EMBED_EDIT_LOGS"]

    move_keys(config, "CENSORING", "WORD_BLACKLIST", "INVITE_WHITELIST")
    config["CENSORING"]["ENABLED"] = config["CENSOR_MESSAGES"]
    del config["CENSOR_MESSAGES"]

    move_keys(config, "INFRACTIONS", "DM_ON_WARN")

def v14(config):
    if len(config["ANTI_SPAM"]) is 0:
        config["ANTI_SPAM"] = {
            "ENABLED": False,
            "BUCKETS": [],
            "EXEMPT_ROLES": [],
            "EXEMPT_USERS": []
        }


def add_logging(config, *args):
    for cid, info in config["LOG_CHANNELS"].items():
        if "FUTURE_LOGS" in info:
            info.extend(args)


def nuke_keys(config, *keys):
    for key in keys:
        if key in config:
            del config[key]


def move_keys(config, section, *keys):
    if section not in config:
        config[section] = dict()
    for key in keys:
        if key in config:
            config[section][key] = config[key]
            del config[key]


# migrators for the configs, do NOT increase the version here, this is done by the migration loop
MIGRATORS = [initial_migration, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14]


async def initialize(bot: commands.Bot):
    global CONFIG_VERSION
    CONFIG_VERSION = Utils.fetch_from_disk("config/template")["VERSION"]
    GearbotLogging.info(f"Current template config version: {CONFIG_VERSION}")
    GearbotLogging.info(f"Loading configurations for {len(bot.guilds)} guilds.")
    for guild in bot.guilds:
        GearbotLogging.info(f"Loading info for {guild.name} ({guild.id}).")
        load_config(guild.id)
        validate_config(guild)


def load_config(guild):
    global SERVER_CONFIGS
    config = Utils.fetch_from_disk(f'config/{guild}')
    if "VERSION" not in config and len(config) < 15:
        GearbotLogging.info(f"The config for {guild} is to old to migrate, resetting")
        config = dict()
    else:
        if "VERSION" not in config:
            config["VERSION"] = 0
        SERVER_CONFIGS[guild] = update_config(guild, config)
    if len(config) is 0:
        GearbotLogging.info(f"No config available for {guild}, creating a blank one.")
        SERVER_CONFIGS[guild] = Utils.fetch_from_disk("config/template")
        save(guild)
    Features.check_server(guild)


def validate_config(guild):
    for key in ["ADMIN_ROLES", "MOD_ROLES", "SELF_ROLES", "TRUSTED_ROLES"]:
        checklist(guild.id, key, guild.get_role)


def checklist(guid, key, getter):
    changed = False
    tr = list()
    cl = get_var(guid, "ROLES", key)
    for c in cl:
        if getter(c) is None:
            tr.append(c)
            changed = True
    for r in tr:
        cl.remove(r)
    if changed:
        save(guid)


def update_config(guild, config):
    v = config["VERSION"]
    while config["VERSION"] < CONFIG_VERSION:
        GearbotLogging.info(f"Upgrading config version from version {v} to {v + 1}")
        d = f"config/backups/v{v}"
        if not os.path.isdir(d):
            os.makedirs(d)
        Utils.save_to_disk(f"{d}/{guild}", config)
        MIGRATORS[config["VERSION"]](config)
        config["VERSION"] += 1
        Utils.save_to_disk(f"config/{guild}", config)

    return config


def get_var(id, section, key=None, default=None):
    if id is None:
        raise ValueError("Where is this coming from?")
    if not id in SERVER_CONFIGS.keys():
        GearbotLogging.info(f"Config entry requested before config was loaded for guild {id}, loading config for it")
        load_config(id)
    s = SERVER_CONFIGS[id].get(section, {})
    if key is not None:
        s = s.get(key, default)
    return s


def set_var(id, cat, key, value):
    SERVER_CONFIGS[id].get(cat, dict())[key] = value
    save(id)
    Features.check_server(id)


def save(id):
    global SERVER_CONFIGS
    with open(f'config/{id}.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(SERVER_CONFIGS[id], indent=4, skipkeys=True, sort_keys=True)))
    Features.check_server(id)


def save_master():
    global MASTER_CONFIG
    with open('config/master.json', 'w') as jsonfile:
        jsonfile.write((json.dumps(MASTER_CONFIG, indent=4, skipkeys=True, sort_keys=True)))


def get_persistent_var(key, default):
    PERSISTENT = Utils.fetch_from_disk("persistent")
    return PERSISTENT[key] if key in PERSISTENT else default


def set_persistent_var(key, value):
    PERSISTENT = Utils.fetch_from_disk("persistent")
    PERSISTENT[key] = value
    Utils.save_to_disk("persistent", PERSISTENT)


def update_config_section(guild_id, section: str, modified_values: dict):
    config_part_types = dict(dict(ConfigTypes._field_types)[section.lower()]._field_types)
    config_part_validators = dict(ConfigTypes._field_types)[section.lower()]

    # Check if their requested update is identical. We don't need to waste CPU cycles and disk writes
    guild_config: dict = get_var(guild_id, section)
    if modified_values.items() <= guild_config.items():
        return dict(updated=False)

    valid_modified_values = {}
    for key, value in modified_values.items():
        key: str = key.lower()
        if key in config_part_types:
            # Check if the primitive type of the value matches
            if type(value) == config_part_types[key]:
                # Validate the key to requirements...
                # Every key has a `validate_KEY` function that can be defined for validation checks
                try:
                    if getattr(config_part_validators, f"validate_{key}")(value):
                        valid_modified_values.update(
                            { f"{key.upper()}": value }
                        )
                    else:
                        # The entire request must be good, no partial updates
                        return dict(
                            error="A configuration key's value is malformed",
                            error_details=f"Value {value} does not conform to requirements!"
                        )
                except AttributeError:
                    # This protects against causing errors due to a value not currently having a validator function
                    return dict(
                        error="Not Implemented",
                        error_details="The current function doesn't yet exist, or won't"
                    )
            else:
                # Inform the API user that a value was the wrong type
                proper_type = str(config_part_types[key]).split("'")[1]
                return dict(
                    error="A configuration value was the wrong type!",
                    error_details=f"Value {value} should be of the type {proper_type}",
                )
        else:
            # Inform the API user tried to change an invalid key
            return dict(
                error="A key could not be found",
                error_details=f"Unknown key: {key.upper()}",
            )

    # If we managed to get here, then all the values were valid and we can write them
    # Check *exactly* what was modifed so we only write what is needed
    changed_values = valid_modified_values.copy()
    for key, value in valid_modified_values.items():
        if guild_config[key] == value:
            changed_values.pop(key)

    guild_config.update(changed_values)
    save(guild_id)
    return dict(updated=True, new_values=get_var(guild_id, section))  # We wrote something to disk
