import asyncio
import json
import uuid

import aioredis
from aioredis.pubsub import Receiver


class Redisception(Exception):

    def __init__(self, message) -> None:
        super().__init__(message)


# thanks mouse
class Messager:

    def __init__(self, inbound, outbound, loop):
        self.loop = loop
        self.conn = None
        self.inbound = inbound
        self.outbound = outbound
        self.receiver = None
        self.task = None
        self.replies = dict()
        self.expected = set()

    async def initialize(self):
        self.conn = await aioredis.create_redis_pool(("localhost", 6379), encoding="utf-8", maxsize=2)
        self.receiver = Receiver(loop=self.loop)
        await self.conn.subscribe(self.receiver.channel(self.inbound))
        self.task = self.loop.create_task(self.fetcher())

        print(f'Redis connection established, listening on {self.inbound}, sending on {self.outbound}')  # FIXME - propper logging


    async def terminate(self):
        # terminate channels and disconnect from redis
        self.conn.unsubscribe(self.inbound)
        self.task.cancel()
        self.receiver.stop()
        self.conn.close()
        await self.conn.wait_closed()

    async def fetcher(self):
        async for sender, message in self.receiver.iter(encoding='utf-8', decoder=json.loads):
            channel = sender.name.decode()
            if channel == self.inbound:
                uid = message["uid"]
                if uid not in self.expected:
                    print("Unexpected message!")
                    print(message)
                else:
                    self.expected.remove(uid)
                    self.replies[uid] = message



    async def get_reply(self, data):
        try:
            return (await asyncio.wait_for(self._get_reply(data), 10))["reply"]
        except TimeoutError:
            raise Redisception("No reply received from the bot!")

    async def _get_reply(self, data):
        uid = str(uuid.uuid4())
        self.expected.add(uid)
        data["uid"] = uid
        await self.conn.publish_json(self.outbound, data)
        while uid not in self.replies:
            await asyncio.sleep(0.1)
        reply = self.replies[uid]
        del self.replies[uid]
        return reply