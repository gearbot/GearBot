import time


def ms_time():
    return int(time.time() * 1000)


class SpamBucket:

    def __init__(self, redis, key_format, max_actions, period):
        self.redis = redis
        self.key_format = key_format
        self.max_actions = max_actions
        self.period = period

    async def incr(self, key, current_time, *, message, channel, user, amt=1, expire=True):
        if expire:
            await self._remove_expired_keys(key, current_time)
        k = self.key_format.format(key)
        for i in range(0, amt):
            await self.redis.zadd(k, current_time, f"{message}-{channel}-{user}-{i}")
        await self.redis.expire(k, self.period)
        return await self.redis.zcount(k)

    async def check(self, key, current_time, amount, *, message, channel, user, expire=True):
        amt = await self.incr(key, current_time, amt=amount, message=message, channel=channel, user=user, expire=expire)
        return amt >= self.max_actions

    async def count(self, key, current_time, expire=True):
        if expire:
            await self._remove_expired_keys(key, current_time)
        k = self.key_format.format(key)
        return await self.redis.zcount(k)

    async def get(self, key, current_time, expire=True):
        if expire:
            await self._remove_expired_keys(key, current_time)
        k = self.key_format.format(key)
        return await self.redis.zrangebyscore(k)

    async def size(self, key, current_time, expire=True):
        if expire:
            await self._remove_expired_keys(key, current_time)
        k = self.key_format.format(key)
        values = await self.redis.zrangebyscore(k)
        if len(values) <= 1:
            return 0
        return (await self.redis.zscore(k, values[-1])) - (await self.redis.zscore(k, values[0]))

    async def clear(self, key):
        k = self.key_format.format(key)
        await self.redis.zremrangebyscore(k)

    async def _remove_expired_keys(self, key, current_time):
        await self.redis.zremrangebyscore(self.key_format.format(key), max=(current_time - self.period))
