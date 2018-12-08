import math
import time
from datetime import datetime

from Util import Utils
from database.DatabaseConnector import Infraction

infractions = Utils.fetch_from_disk("infractions")["infractions"]
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