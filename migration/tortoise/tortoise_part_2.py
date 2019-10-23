import json
import asyncio
from datetime import datetime

from tortoise import run_async

from database import Models
from database.Models import Infraction

async def execute():
    await Models.init()
    print("Migrating infractions, this can take a while!")

    with open("infractions.json", "r") as file:
        s = file.read()
        l = json.loads(s)
        loaded = {k: dict(start=datetime.fromisoformat(v["start"]), end=datetime.fromisoformat(v["end"]) if v["end"] is not None else None) for k, v in l.items()}

    created = 0
    for k, v in loaded.items():
        await Infraction.filter(id=k).update(start=v["start"], end=v["end"])
        created += 1
        if created % 100 == 0:
            await asyncio.sleep(0)
    print(f"Finished migrating {len(loaded)} infractions")


run_async(execute())