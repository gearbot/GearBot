import asyncio

from pytz import UnknownTimeZoneError, timezone

from Util import GearbotLogging, Utils, Translator, Configuration, Permissioncheckers
from database.DatabaseConnector import Infraction

BOT = None


def initialize(bot_in):
    global BOT
    BOT = bot_in


class ValidationException(Exception):
    def __init__(self, errors) -> None:
        self.errors = errors


def check_type(valid_type, allow_none=False, **illegal):
    def checker(guild, value, preview, user, *_):
        if value is None and not allow_none:
            return "This value can not be none"
        if not isinstance(value, valid_type):
            return f"This isn't a {valid_type}"
        if value in illegal:
            return "This value is not allowed"
        return True

    return checker


def validate_list_type(valid_type, allow_none=False, **illegal):
    def checker(guild, bad_list, preview, user, *_):
        for value in bad_list:
            if value is not None and not allow_none:
                return f"A value in the group, '{value}', was not defined!"
            if not isinstance(value, valid_type):
                return f"A value in the group, '{value}', is the wrong type! It should be a {valid_type}"
            if value in illegal:
                return f"A value in the group, '{value}', is not allowed!"
            return True

    return checker


def validate_timezone(guild, value, preview, user, *_):
    try:
        timezone(value)
        return True
    except UnknownTimeZoneError:
        return "Unknown timezone"


def validate_role(allow_everyone=False, allow_zero=False):
    def validator(guild, role_id, preview, user, new_values):
        role_type = list(new_values.keys())[0]

        role = guild.get_role(role_id)
        if role is None and not allow_zero:
            return "Unable to find a role with that id on the server"
        if guild.id == role_id and not allow_everyone:
            return "You can't use the '@everyone' role here!"
        if role_type == "SELF_ROLES":
            role = guild.get_role(role)
            if not(guild.me.top_role > role and role.managed == False):
                return "The specified role can not be managed by Gearbot!"

        return True

    return validator


def validate_role_list(guild, role_list, preview, user, new_values):
    rolelist_type = list(new_values.keys())[0]

    last_role_id = None
    for role_id in role_list:
        # Make sure the roles are the right type
        if not isinstance(role_id, int):
            return f"One of the roles, '{role}', is not a integer!"

        # Check if the role exists
        if role_id is None:
            return f"One of the roles, '{role}', is not valid!"

        if role_id == guild.id:
            return "You can't use the '@everyone' role here!"
        
        # Validate that there are no duplicate roles in the list
        if role_id == last_role_id:
            return f"The role '{role}' was specified twice!"

        if rolelist_type == "SELF_ROLES":
            role = guild.get_role(role_id)
            if not(guild.me.top_role > role and role.managed == False):
                return f"The specified role, {role_id}, can not be managed by Gearbot!"

        last_role = role_id

    return True


def check_number_range(lower, upper):
    def checker(guild, value, preview, user, *_):
        if value < lower:
            return f"Value too low, must be at least {lower}"
        if value > upper:
            return f"Value too high, must be at most {upper}"
        return True

    return checker


def multicheck(*args):
    def check(*checkargs):
        for arg in args:
            validator = arg(*checkargs)
            if validator is not True:
                return validator
        return True

    return check


def perm_range_check(lower, upper, other_min=None):
    def check(guild, value, preview, user, *_):
        user_lvl = Permissioncheckers.user_lvl(user)
        new_upper = min(upper, user_lvl)
        new_lower = lower
        if other_min is not None:
            new_lower = max(lower, preview[other_min])
        return check_number_range(new_lower, new_upper)(guild, value, preview, user)

    return check


VALIDATORS = {
    "GENERAL": {
        "PREFIX": multicheck(
            check_type(str),
            lambda g, v, *_: "Prefix too long" if len(v) > 10 else "Prefix can't be blank" if len(v) is 0 else True),

        "LANG": lambda g, v, *_: v in Translator.LANGS or "Unknown language",
        "PERM_DENIED_MESSAGE": check_type(bool),
        "TIMESTAMPS": check_type(bool),
        "NEW_USER_THRESHOLD": multicheck(check_type(int), check_number_range(0, 60 * 60 * 24 * 14)),
        "TIMEZONE": validate_timezone
    },
    "PERMISSIONS": {
        "LVL4_ROLES": validate_role_list,
        "ADMIN_ROLES": validate_role_list,
        "MOD_ROLES": validate_role_list,
        "TRUSTED_ROLES": validate_role_list,
    },
    "ROLES": {
        "SELF_ROLES": validate_role_list,
        "ROLE_LIST": validate_role_list,
        "ROLE_WHITELIST": check_type(bool),
        "MUTE_ROLE": multicheck(check_type(int), validate_role(allow_zero=True))
    },
    "DASH_SECURITY": {
        "ACCESS": perm_range_check(1, 5),
        "INFRACTION": perm_range_check(1, 5, other_min="ACCESS"),
        "VIEW_CONFIG": perm_range_check(1, 5, other_min="ACCESS"),
        "ALTER_CONFIG": perm_range_check(2, 5, other_min="VIEW_CONFIG")
    }
}


def role_list_logger(t):
    def handler(guild, old, new, user_parts):
        removed = list(set(old) - set(new))
        added = list(set(new) - set(old))
        for r in removed:
            role = guild.get_role(int(r))
            role_name = Utils.escape_markdown(role.name) if role is not None else r
            GearbotLogging.log_to(
                guild.id, 
                f"config_change_role_removed", 
                role_name=role_name, role_id=r, type=t,
                **user_parts
            )

        for r in added:
            role = guild.get_role(int(r))
            role_name = Utils.escape_markdown(role.name) if role is not None else r
            GearbotLogging.log_to(
                guild.id,
                f"config_change_role_added", 
                role_name=role_name, 
                role_id=r, 
                type=t,
                **user_parts
            )

    return handler


async def role_remover(active_mutes, guild, role):
    for mute in active_mutes:
        member = guild.get_member(mute.user_id)
        if member is not None:
            await member.remove_roles(role)


async def role_adder(active_mutes, guild, role):
    for mute in active_mutes:
        member = guild.get_member(mute.user_id)
        if member is not None:
            await member.add_roles(role)


def swap_mute_role(guild, old, new, parts):
    active_mutes = Infraction.select().where(
        (Infraction.type == "Mute") & (Infraction.guild_id == guild.id) & Infraction.active)

    loop = asyncio.get_running_loop()

    old_role = guild.get_role(old)
    new_role = guild.get_role(new)
    parts.update(
        old_id=old,
        old_name=Utils.escape_markdown(old_role.name) if old_role is not None else old,
        new_id=new,
        new_name=Utils.escape_markdown(new_role.name) if new_role is not None else new,
    )

    if old != 0:
        if old_role is not None:
            loop.create_task(role_remover(active_mutes, guild, old_role))
        if new != 0:
            GearbotLogging.log_to(guild.id, "config_mute_role_changed", **parts)
        else:
            GearbotLogging.log_to(guild.id, "config_mute_role_disabled", **parts)
    if new != 0:
        if new_role is not None:
            loop.create_task(role_adder(active_mutes, guild, new_role))
        if old == 0:
            GearbotLogging.log_to(guild.id, "config_mute_role_set", **parts)


def self_role_updater(guild, old, new, parts):
    role_list_logger("SELF")(guild, old, new, parts)
    BOT.dispatch("self_roles_update", guild.id)


def dash_perm_change_logger(t):
    def handler(guild, old, new, parts):
        GearbotLogging.log_to(
            guild.id, 
            f"config_dash_security_change",
            type=Translator.translate(f'config_dash_security_{t.lower()}', guild.id),
            old=Translator.translate(f'perm_lvl_{old}', guild.id),
            new=Translator.translate(f'perm_lvl_{new}', guild.id), **parts
        )

    return handler


SPECIAL_HANDLERS = {
    "ROLES": {
        "MUTE_ROLE": swap_mute_role,
        "SELF_ROLES": self_role_updater,
    },
    "PERMISSIONS": {
        "LVL4_ROLES": role_list_logger("LVL4"),
        "ADMIN_ROLES": role_list_logger("ADMIN"),
        "MOD_ROLES": role_list_logger("MOD"),
        "TRUSTED_ROLES": role_list_logger("TRUSTED"),
    },
    "DASH_SECURITY": {
        "ACCESS": dash_perm_change_logger("ACCESS"),
        "INFRACTION": dash_perm_change_logger("INFRACTION"),
        "VIEW_CONFIG": dash_perm_change_logger("VIEW_CONFIG"),
        "ALTER_CONFIG": dash_perm_change_logger("ALTER_CONFIG")
    }
}


def is_numeric(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


def update_config_section(guild, section, new_values, user):
    fields = VALIDATORS[section]
    errors = dict()
    guild_config = Configuration.get_var(guild.id, section)

    new_values = {
        k: [int(rid) if is_numeric(rid) else rid for rid in v] if isinstance(v, list) else int(v) if is_numeric(
            v) else v for k, v in new_values.items()}

    modified_values = new_values.copy()
    preview = guild_config.copy()
    preview.update(**new_values)

    for k, v in new_values.items():
        if k not in fields:
            errors[k] = "Unknown key"
        elif guild_config[k] == v:
            modified_values.pop(k)
        else:
            validated = fields[k](guild, v, preview, user, new_values)
            if validated is not True:
                errors[k] = validated

    if len(modified_values) is 0:
        errors[section] = "Nothing to save!"
    if len(errors) > 0:
        raise ValidationException(errors)

    user_parts = {
        "user": Utils.clean_user(user),
        "user_id": user.id
    }
    old = dict(**guild_config)
    guild_config.update(**modified_values)
    Configuration.save(guild.id)

    for k, v in modified_values.items():
        if section in SPECIAL_HANDLERS and k in SPECIAL_HANDLERS[section]:
            SPECIAL_HANDLERS[section][k](guild, old[k], modified_values[k], user_parts)
        else:
            GearbotLogging.log_to(
                guild.id, 
                "config_change",
                option_name=Translator.translate(f"config_{section}_{k}".lower(), guild),
                old=old[k], new=modified_values[k], **user_parts
            )

    to_return = {
        k: [str(rid) if isinstance(rid, int) else rid for rid in v] if isinstance(v, list) 
        else str(v) if isinstance(v, int) else v for k, v in guild_config.items()
    }
    return dict(status="Updated", modified_values=to_return)
