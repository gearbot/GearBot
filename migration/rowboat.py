import json
import math
import time
from datetime import datetime

from peewee import PrimaryKeyField, Model, BigIntegerField, CharField, TimestampField, BooleanField, MySQLDatabase


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
last_reported = -1
t = time.time()
for i in infractions:
    start = datetime.strptime(i["created_at"], "%a, %d %b %Y %H:%M:%S %Z")
    end = datetime.strptime(i["expires_at"], "%a, %d %b %Y %H:%M:%S %Z") if i["expires_at"] is not None else None
    Infraction.create(id=i["id"], guild_id=i["guild"]["id"], user_id=i["user"]["id"], mod_id=i["actor"]["id"],
                      type=i["type"]["name"], reason=i["reason"] if i["reason"] is not None else "No reason specified",
                      start=start, end=end, active=i["active"] == 'true')
    done += 1
    percent = math.floor((done/len(infractions)) * 100)
    if percent > last_reported:
        last_reported = percent
        print(f"{percent}% done, {len(infractions) - done} to go")
print(f"Imported everything in {round((time.time() - t))} seconds")