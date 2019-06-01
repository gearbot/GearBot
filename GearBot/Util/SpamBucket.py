import time


def ms_time():
    return int(time.time() * 1000)


class SpamBucket:

    def __init__(self, redis, key_format, max_actions, period):
        self.redis = redis
        self.key_format = key_format
        self.max_actions = max_actions
        self.period = period

    async def incr(self, key, amt=1):
        await self._remove_expired_keys(key)
        key = self.key_format.format(key)
        for i in range(0, amt):
            await self.redis.zadd(key, ms_time(), f"{ms_time()}-{i}")
        await self.redis.expire(key, self.period)
        return await self.redis.zcount(key)

    async def check(self, key, amount=1):
        await self._remove_expired_keys(key)
        key = self.key_format.format(key)
        amt = await self.incr(key, amount)
        print(f"{amt}/{self.max_actions}")
        return amt >= self.max_actions

    async def count(self, key):
        await self._remove_expired_keys(key)
        key = self.key_format.format(key)
        return await self.redis.zcount(key)

    async def size(self, key):
        await self._remove_expired_keys(key)
        key = self.key_format.format(key)
        values = await self.redis.zrangebyscore(key)
        if len(values) <= 1:
            return 0
        return (await self.redis.zscore(key, values[:-1])) - (await self.redis.zscore(key, values[0]))

    async def clear(self, key):
        key = self.key_format.format(key)
        await self.redis.zremrangebyscore(key)

    async def _remove_expired_keys(self, key):
        self.redis.zremrangebyscore(self.key_format.format(key), max=(ms_time() - (self.period * 1000)))
