import prometheus_client as prom
from prometheus_client.metrics import Info


class PromMonitors:
    def __init__(self, bot, prefix) -> None:
        self.command_counter = prom.Counter(f"{prefix}_commands_ran", "How many times commands were ran", [
            "command_name",
            "cluster"
        ])


        self.user_message_raw_count = prom.Counter(f"{prefix}_user_message_raw_count", "Raw count of how many messages we have seen from users", ["cluster"])
        self.bot_message_raw_count = prom.Counter(f"{prefix}_bot_message_raw_count",
                                                  "Raw count of how many messages we have seen from bots", ["cluster"])
        self.own_message_raw_count = prom.Counter(f"{prefix}_own_message_raw_count", "Raw count of how many messages GearBot has send", ["cluster"])

        self.bot_guilds = prom.Gauge(f"{prefix}_guilds", "How many guilds the bot is in", ["cluster"])

        self.bot_users = prom.Gauge(f"{prefix}_users", "How many users the bot can see", ["cluster"])
        self.bot_users_unique = prom.Gauge(f"{prefix}_users_unique", "How many unique users the bot can see", ["cluster"])
        self.bot_event_counts = prom.Counter(f"{prefix}_event_counts", "How much each event occurred", ["event_name", "cluster"])

        self.bot_latency = prom.Gauge(f"{prefix}_latency", "Current bot latency", ["cluster"])

        self.uid_usage = prom.Counter(f"{prefix}_context_uid_usage", "Times uid was used from the context command", ["type", "cluster"])
        self.userinfo_usage = prom.Counter(f"{prefix}_context_userinfo_usage", "Times userinfo was used from the context command", ["type", "cluster"])
        self.inf_search_usage = prom.Counter(f"{prefix}_context_inf_search_usage", "Times inf serach was used from the context command", ["type", "cluster"])

        bot.metrics_reg.register(self.command_counter)
        bot.metrics_reg.register(self.user_message_raw_count)
        bot.metrics_reg.register(self.bot_message_raw_count)
        bot.metrics_reg.register(self.bot_guilds)
        bot.metrics_reg.register(self.bot_users)
        bot.metrics_reg.register(self.bot_users_unique)
        bot.metrics_reg.register(self.bot_event_counts)
        bot.metrics_reg.register(self.own_message_raw_count)
        bot.metrics_reg.register(self.bot_latency)
        bot.metrics_reg.register(self.uid_usage)
        bot.metrics_reg.register(self.userinfo_usage)
        bot.metrics_reg.register(self.inf_search_usage)
