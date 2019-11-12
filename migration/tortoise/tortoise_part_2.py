import json
import asyncio
from datetime import datetime

from tortoise import run_async, Tortoise
from InfractionModels import Infraction


async def execute():
    await Tortoise.init(
        db_url="mysql://gearbot:password@localhost:3306/gearbot?minsize=1&maxsize=10",
        modules={'models': ['InfractionModels']}
    )
    print("Migrating infractions, this can take a while!")

    with open("infractions.json", "r") as file:
        s = file.read()
        l = json.loads(s)
        loaded = {k: dict(start=datetime.fromisoformat(v["start"]), end=datetime.fromisoformat(v["end"]) if v["end"] is not None else None) for k, v in l.items()}
    await asyncio.gather(*[Infraction.filter(id=k).update(start=v["start"], end=v["end"]) for k, v in loaded.items()])
    print(f"Finished migrating {len(loaded)} infractions")


run_async(execute())