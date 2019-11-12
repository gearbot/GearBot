from datetime import datetime
import json

from tortoise import run_async, Tortoise

from InfractionModels import InfractionMigration


async def prep():
    await Tortoise.init(
        db_url="mysql://gearbot:password@localhost:3306/gearbot?minsize=1&maxsize=10",
        modules={'models': ['InfractionModels']}
    )
    print("Collecting infractions for migration...")
    converted = {i.id: dict(start=datetime.utcfromtimestamp(i.start).isoformat(),
                            end=datetime.utcfromtimestamp(i.end).isoformat() if i.end is not None else None) for i in
                 await InfractionMigration.all()}
    with open("infractions.json", "w") as file:
        file.write(json.dumps(converted))
    print(f"Backed up {len(converted)} infractions for migration")


run_async(prep())
