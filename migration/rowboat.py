import json
import math
import time
from datetime import datetime

from peewee import PrimaryKeyField, Model, BigIntegerField, CharField, TimestampField, BooleanField, MySQLDatabase, \
    IntegrityError


def fetch_from_disk(filename, alternative=None):
    try:
        with open(f"{filename}.json") as file:
            return json.load(file)
    except FileNotFoundError:
        if alternative is not None:
            fetch_from_disk(alternative)
        return dict()


c = fetch_from_disk("../config/master")

connection = MySQLDatabase(c["DATABASE_NAME"],
                           user=c["DATABASE_USER"],
                           password=c["DATABASE_PASS"],
                           host=c["DATABASE_HOST"],
                           port=c["DATABASE_PORT"], use_unicode=True, charset="utf8mb4")


class Infraction(Model):
    id = PrimaryKeyField()
    guild_id = BigIntegerField()
    user_id = BigIntegerField()
    mod_id = BigIntegerField()
    type = CharField(max_length=10, collation="utf8mb4_general_ci")
    reason = CharField(max_length=2000, collation="utf8mb4_general_ci")
    start = TimestampField()
    end = TimestampField(null=True)
    active = BooleanField(default=True)

    class Meta:
        database = connection


infractions = fetch_from_disk("infractions")["infractions"]
print(f"Importing {len(infractions)}, this can take a while...")
done = 0
dupes = 0
moved = 0
last_reported = -1
t = time.time()
for i in infractions:
    # extract info
    start = datetime.strptime(i["created_at"], "%a, %d %b %Y %H:%M:%S %Z")
    end = datetime.strptime(i["expires_at"], "%a, %d %b %Y %H:%M:%S %Z") if i["expires_at"] is not None else None
    reason = i["reason"] if i["reason"] is not None else "No reason specified"
    active = i["active"] == 'true'
    guild_id = int(i["guild"]["id"])
    user_id = int(i["user"]["id"])
    mod_id = int(i["actor"]["id"])
    type = i["type"]["name"]
    try:
        # attempt insertion
        Infraction.create(id=i["id"], guild_id=guild_id, user_id=user_id, mod_id=mod_id, type=type, reason=reason,
                          start=start, end=end, active=active)
    except IntegrityError:
        # failed, retrieve infraction occupying this
        infraction = Infraction.get_by_id(i["id"])

        # make sure it's not a dupe
        if infraction.guild_id != guild_id or infraction.user_id != user_id or infraction.mod_id != mod_id or type != infraction.type \
            or infraction.reason != reason or infraction.start != start or infraction.end != end or infraction.active != active:
            Infraction.create(guild_id=guild_id, user_id=user_id, mod_id=mod_id, type=type, reason=reason,
                              start=start, end=end, active=active)
            moved += 1
        else:
            dupes += 1

    done += 1
    percent = math.floor((done / len(infractions)) * 100)
    if percent > last_reported:
        last_reported = percent
        print(f"{percent}% done, {len(infractions) - done} to go")

#reporting
print(f"Initial import completed in {round((time.time() - t))} seconds")
print(f"Imported: {done - dupes}")
print(f"Dupes: {dupes}")
print(f"{moved} reports had to be assigned a new ID")
