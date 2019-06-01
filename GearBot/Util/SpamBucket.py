import time


def ms_time():
    return int(time.time() * 1000)


class SpamBucket:

    def __init__(self, redis, key_format, max_actions, period):
        self.redis = redis
        self.key_format = key_format
        self.max_actions = max_actions
        self.period = period

    def incr(self, key, amt=1):
        self._remove_expired_keys(key)
        key = self.key_format.format(key)
        for i in range(0, amt):
            self.redis.zadd(key, ms_time(), f"{ms_time()}-{i}")
        self.redis.expire(key, self.period)
        return self.redis.zcount(key)

    def check(self, key, amount=1):
        self._remove_expired_keys(key)
        key = self.key_format.format(key)
        return self.incr(key, amount) >= self.max_actions

    def count(self, key):
        self._remove_expired_keys(key)
        key = self.key_format.format(key)
        return self.redis.zcount(key)

    def size(self, key):
        self._remove_expired_keys(key)
        key = self.key_format.format(key)
        values = self.redis.zrangebyscore(key)
        if len(values) <= 1:
            return 0
        return self.redis.zscore(key, values[:-1]) - self.redis.zscore(key, values[0])

    def clear(self, key):
        key = self.key_format.format(key)
        self.redis.zremrangebyscore(key)

    def _remove_expired_keys(self, key):
        self.redis.zremrangebyscore(self.key_format.format(key), max=(ms_time() - (self.period * 1000)))
