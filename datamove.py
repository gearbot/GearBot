import logging
import sys

from tortoise import Model, fields, Tortoise, run_async


class LoggedMessage(Model):
    messageid = fields.BigIntField(pk=True, generated=False)
    content = fields.CharField(max_length=2000, collation="utf8mb4_general_ci", null=True)
    author = fields.BigIntField()
    channel = fields.BigIntField()
    server = fields.BigIntField()
    type = fields.IntField(null=True)
    pinned = fields.BooleanField(default=False)

    class Meta:
        app = "models"

class NewLoggedMessage(Model):
    messageid = fields.BigIntField(pk=True, generated=False)
    content = fields.CharField(max_length=2000, collation="utf8mb4_general_ci", null=True)
    author = fields.BigIntField()
    channel = fields.BigIntField()
    server = fields.BigIntField()
    type = fields.IntField(null=True)
    pinned = fields.BooleanField(default=False)

    class Meta:
        app = "new"


class LoggedAttachment(Model):
    id = fields.BigIntField(pk=True, generated=False)
    name = fields.CharField(max_length=100)
    isImage = fields.BooleanField()
    message = fields.ForeignKeyField("models.LoggedMessage", related_name='attachments', source_field='message_id')

    class Meta:
        app = "models"


class NewLoggedAttachment(Model):
    id = fields.BigIntField(pk=True, generated=False)
    name = fields.CharField(max_length=100)
    isImage = fields.BooleanField()
    message = fields.ForeignKeyField("models.LoggedMessage", related_name='attachments', source_field='message_id')

    class Meta:
        app = "new"


class CustomCommand(Model):
    id = fields.IntField(pk=True, generated=True)
    serverid = fields.BigIntField()
    trigger = fields.CharField(max_length=20, collation="utf8mb4_general_ci")
    response = fields.CharField(max_length=2000, collation="utf8mb4_general_ci")
    created_by = fields.BigIntField(null=True)

    class Meta:
        app = "models"


class NewCustomCommand(Model):
    id = fields.IntField(pk=True, generated=True)
    serverid = fields.BigIntField()
    trigger = fields.CharField(max_length=20, collation="utf8mb4_general_ci")
    response = fields.CharField(max_length=2000, collation="utf8mb4_general_ci")
    created_by = fields.BigIntField(null=True)

    class Meta:
        app = "new"


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

    class Meta:
        app = "models"

class NewInfraction(Model):
    id = fields.IntField(pk=True, generated=True)
    guild_id = fields.BigIntField()
    user_id = fields.BigIntField()
    mod_id = fields.BigIntField()
    type = fields.CharField(max_length=10, collation="utf8mb4_general_ci")
    reason = fields.CharField(max_length=2000, collation="utf8mb4_general_ci")
    start = fields.BigIntField()
    end = fields.BigIntField(null=True)
    active = fields.BooleanField(default=True)

    class Meta:
        app = "new"


class Reminder(Model):
    id = fields.IntField(pk=True, generated=True)
    user_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    guild_id = fields.CharField(max_length=20, null=True)
    message_id = fields.BigIntField()
    dm = fields.BooleanField()
    to_remind = fields.CharField(max_length=1800, collation="utf8mb4_general_ci")
    send = fields.BigIntField(null=True)
    time = fields.BigIntField()
    status = fields.IntField()

    class Meta:
        app = "models"


class NewReminder(Model):
    id = fields.IntField(pk=True, generated=True)
    user_id = fields.BigIntField()
    channel_id = fields.BigIntField()
    guild_id = fields.CharField(max_length=20, null=True)
    message_id = fields.BigIntField(null=True)
    dm = fields.BooleanField()
    to_remind = fields.CharField(max_length=1800, collation="utf8mb4_general_ci")
    send = fields.BigIntField(null=True)
    time = fields.BigIntField()
    status = fields.IntField()

    class Meta:
        app = "new"


LOGGER = logging.getLogger('datamover')
LOGGER.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
LOGGER.addHandler(handler)

async def run():
    old_url = input("Source database url: ")
    new_url = input("Destination database url: ")
    await Tortoise.init(
        config={
            'connections': {
                'old': old_url,
                'new': new_url
            },
            'apps': {
                'my_app': {
                    'models': ['__main__'],
                    # If no default_connection specified, defaults to 'default'
                    'default_connection': 'old',
                },
                'models': {'models': ['__main__'], 'default_connection': 'old'}
            }
        }
    )
    new = Tortoise.get_connection('new')
    LOGGER.info("Database connections established")


    LOGGER.info("Staring custom commands migration")
    ccs = await CustomCommand.filter()
    LOGGER.info(f"Found {len(ccs)} custom commands, migrating...")
    await CustomCommand.bulk_create([NewCustomCommand(id=cc.id, serverid=cc.serverid, trigger=cc.trigger, response=cc.response,created_by=cc.created_by) for cc in ccs], new)
    await new.execute_script("select setval('customcommand_id_seq', (select max(id) from customcommand))")
    LOGGER.info("Custom commands migrated")


    LOGGER.info("Starting reminders migration")
    reminders = await Reminder.filter()
    LOGGER.info(f"Found {len(reminders)} reminders, migrating...")
    await Reminder.bulk_create([NewReminder(id=reminder.id, user_id=reminder.user_id, channel_id=reminder.channel_id, guild_id=reminder.guild_id, message_id=reminder.message_id, dm=reminder.dm, to_remind=reminder.to_remind, send=reminder.send, time=reminder.time, status=reminder.status) for reminder in reminders], new)
    await new.execute_script("select setval('reminder_id_seq', (select max(id) from reminder))")
    LOGGER.info("Reminders migrated")

    LOGGER.info("Starting infractions migration")
    todo = await Infraction.filter().count()
    LOGGER.info(f"Found {todo} infractions to migrate")
    done = 0
    while done < todo:
        chunk = await Infraction.filter().offset(done).limit(10000)
        new_infractions=[NewInfraction(id=infraction.id, guild_id=infraction.guild_id, user_id=infraction.user_id, mod_id=infraction.mod_id, type=infraction.type, reason=infraction.reason, start=infraction.start, end=infraction.end, active=infraction.active) for infraction in chunk]
        await Infraction.bulk_create(new_infractions, new)
        done += len(new_infractions)
        LOGGER.info(f"{done}/{todo} infractions migrated...")
    await new.execute_script("select setval('infraction_id_seq', (select max(id) from infraction))")
    LOGGER.info("Infractions migrated")

    LOGGER.info("Starting logged messages migration")
    todo = await LoggedMessage.filter().count()
    LOGGER.info(f"Found {todo} logged messages to migrate")
    done = 0
    while done < todo:
        chunk = await LoggedMessage.filter().order_by("-messageid").offset(done).limit(10000)
        new_messages=[NewLoggedMessage(messageid=message.messageid, content=message.content, author=message.author, channel=message.channel, server=message.server, type=message.type, pinned=message.pinned) for message in chunk]
        try:
            await LoggedMessage.bulk_create(new_messages, new)
        except:
            LOGGER.error("Logged message chunk failed!")
        done += len(new_messages)
        LOGGER.info(f"{done}/{todo} logged messages migrated...")
    LOGGER.info("Logged messages migrated")


    LOGGER.info("Starting logged attachments migration")
    todo = await LoggedAttachment.filter().count()
    LOGGER.info(f"Found {todo} logged attachments to migrate")
    done = 0
    while done < todo:
        chunk = await LoggedAttachment.filter().order_by("-id").offset(done).limit(10000)
        new_attachments=[NewLoggedAttachment(id=attachment.id, name=attachment.name, message=attachment.message, isImage=attachment.isImage) for attachment in chunk]
        await LoggedAttachment.bulk_create(new_attachments, new)
        done += len(new_attachments)
        LOGGER.info(f"{done}/{todo} logged attachments migrated...")
    LOGGER.info("Logged attachments migrated")








run_async(run())
