from playhouse.migrate import *

from Util import Configuration
from database.DatabaseConnector import Infraction

connection = MySQLDatabase(Configuration.get_master_var("DATABASE_NAME"),
                               user=Configuration.get_master_var("DATABASE_USER"),
                               password=Configuration.get_master_var("DATABASE_PASS"),
                               host=Configuration.get_master_var("DATABASE_HOST"),
                               port=Configuration.get_master_var("DATABASE_PORT"), use_unicode=True, charset="utf8mb4")

#make connection
migrator = MySQLMigrator(connection)

#run everything in a transaction so we don't turn the database into 💩 if something goes wrong
with connection.atomic():
    #fields to add
    end = TimestampField(null=True)
    active = BooleanField(default=True)
    #add fields
    migrate(
        migrator.add_column("infraction", "end", end),
        migrator.add_column("infraction", "active", active),
        migrator.rename_column("infraction", "timestamp", "start"),
    )

    #some infractions are not active anymore
    Infraction.update(active=False).where((Infraction.type == "Mute") | (Infraction.type == "Kick")).execute()
