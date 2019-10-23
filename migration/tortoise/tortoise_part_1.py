from datetime import datetime
import json

from tortoise import run_async, Tortoise

from Util import Configuration
from migration.tortoise import InfractionMigration


async def prep():
    await Tortoise.init(
        db_url=Configuration.get_master_var("DATABASE"),
        modules={'models': ['migration.tortoise.InfractionMigration']}
    )
    print("Collecting infractions for migration...")
    converted = {i.id: dict(start=datetime.utcfromtimestamp(i.start).isoformat(),
                            end=datetime.utcfromtimestamp(i.end).isoformat() if i.end is not None else None) for i in
                 await InfractionMigration.all()}
    with open("infractions.json", "w") as file:
        file.write(json.dumps(converted))
    print(f"Backed up {len(converted)} infractions for migration")


run_async(prep())
