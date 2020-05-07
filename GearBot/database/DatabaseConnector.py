from tortoise.models import Model
from tortoise import fields, Tortoise

from Util import Configuration


class LoggedMessage(Model):
    messageid = fields.BigIntField(pk=True, generated=False)
    content = fields.CharField(max_length=2000, collation="utf8mb4_general_ci", null=True)
    author = fields.BigIntField()
    channel = fields.BigIntField()
    server = fields.BigIntField()
    type = fields.IntField(null=True)
    pinned = fields.BooleanField(default=False)


class LoggedAttachment(Model):
    id = fields.BigIntField(pk=True, generated=False)
    name = fields.CharField(max_length=100)
    isImage = fields.BooleanField()
    message = fields.ForeignKeyField("models.LoggedMessage", related_name='attachments', source_field='message_id')


class CustomCommand(Model):
    id = fields.IntField(pk=True, generated=True)
    serverid = fields.BigIntField()
    trigger = fields.CharField(max_length=20, collation="utf8mb4_general_ci")
    response = fields.CharField(max_length=2000, collation="utf8mb4_general_ci")



class Infraction(Model):
    id = fields.IntField(pk=True, generated=True)
    guild_id = fields.BigIntField()
    user_id = fields.BigIntField()
    mod_id = fields.BigIntField()
    type = fields.CharField(max_length=10, collation="utf8mb4_general_ci")
    reason = fields.CharField(max_length=2000, collation="utf8mb4_general_ci")
    start = fields.BigIntField()
    end = fields.BigIntField(null=True)
    active = fields.BooleanField(default=True)


class Reminder(Model):
    id = fields.IntField(pk=True, generated=True)
    user_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    guild_id = fields.CharField(max_length=20)
    message_id = fields.BigIntField()
    dm = fields.BooleanField()
    to_remind = fields.CharField(max_length=1800, collation="utf8mb4_general_ci")
    send = fields.BigIntField(null=True)
    time = fields.BigIntField()
    status = fields.IntField()



class Raid(Model):
    id = fields.IntField(pk=True, generated=True)
    guild_id = fields.BigIntField()
    start = fields.BigIntField()
    end = fields.BigIntField(null=True)


class Raider(Model):
    id = fields.IntField(pk=True, generated=True)
    raid = fields.ForeignKeyField("models.Raid", related_name="raiders", source_field="raid_id")
    user_id = fields.BigIntField()
    joined_at = fields.BigIntField()


class RaidAction(Model):
    id = fields.IntField(pk=True, generated=True)
    raider = fields.ForeignKeyField("models.Raider", related_name="actions_taken", source_field="raider_id")
    action = fields.CharField(max_length=20)
    infraction = fields.ForeignKeyField("models.Infraction", related_name="RaiderAction", source_field="infraction_id", null=True)


async def init():
    await Tortoise.init(
        db_url=f"mysql://{Configuration.get_master_var('DATABASE_USER')}:{Configuration.get_master_var('DATABASE_PASS')}@{Configuration.get_master_var('DATABASE_HOST')}:{Configuration.get_master_var('DATABASE_PORT')}/{Configuration.get_master_var('DATABASE_NAME')}",
        modules={"models": ["database.DatabaseConnector"]}
    )
