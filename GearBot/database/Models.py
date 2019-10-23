from tortoise import Tortoise
from tortoise.fields import BigIntField, CharField, IntField, BooleanField, ForeignKeyField, DatetimeField
from tortoise.models import Model

from Util import Configuration, GearbotLogging
from Util.Enums import ReminderStatus
from database.EnumField import EnumField


class LoggedMessage(Model):
    id = BigIntField(pk=True, generated=False)
    content = CharField(max_length=2000, collation="utf8mb4_general_ci", null=True)
    author = BigIntField()
    channel = BigIntField()
    server = BigIntField()
    type = IntField(null=True)
    pinned = BooleanField(default=False)


class LoggedAttachment(Model):
    id = BigIntField(pk=True, generated=False)
    name = CharField(max_length=100)
    isImage = BooleanField()
    message = ForeignKeyField("models.LoggedMessage", related_name="attachments")


class CustomCommand(Model):
    id = IntField(pk=True)
    serverid = BigIntField()
    trigger = CharField(max_length=20, collation="utf8mb4_general_ci")
    response = CharField(max_length=2000, collation="utf8mb4_general_ci")


class Infraction(Model):
    id = IntField(pk=True)
    guild_id = BigIntField()
    user_id = BigIntField()
    mod_id = BigIntField()
    type = CharField(max_length=10, collation="utf8mb4_general_ci")
    reason = CharField(max_length=2000, collation="utf8mb4_general_ci")
    start = DatetimeField()
    end = DatetimeField(null=True)
    active = BooleanField(default=True)


class Reminder(Model):
    id = IntField(pk=True)
    user_id = BigIntField()
    channel_id = BigIntField()
    guild_id = CharField(max_length=20)
    message_id = BigIntField()
    dm = BooleanField()
    to_remind = CharField(max_length=1800, collation="utf8mb4_general_ci")
    send = DatetimeField()
    time = DatetimeField()
    status = EnumField(ReminderStatus)


class Raid(Model):
    id = IntField(pk=True)
    guild_id = BigIntField()
    start = DatetimeField()
    end = DatetimeField(null=True)


class Raider(Model):
    id = IntField(pk=True)
    raid = ForeignKeyField("models.Raid", related_name="raiders")
    user_id = BigIntField()
    joined_at = DatetimeField()


class RaidAction(Model):
    id = IntField(pk=True)
    raider = ForeignKeyField("models.Raider", related_name="actions_taken")
    action = CharField(max_length=20)
    infraction = ForeignKeyField("models.Infraction", related_name="RaiderActions", null=True)



async def init():
    GearbotLogging.info("Initializing database connection")
    await Tortoise.init(
        db_url=Configuration.get_master_var("DATABASE"),
        modules={'models': ['database.Models']}
    )
    GearbotLogging.info("Database initialized")


async def disconnect():
    GearbotLogging.info("Disconnecting database")
    await Tortoise.close_connections()
    GearbotLogging.info("Database disconnected")
