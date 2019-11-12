import prometheus_client as prom

class PromMonitors:
    def __init__(self, bot) -> None:
        self.command_counter = prom.Counter("commands_ran", "How many times commands were ran", [
            "command_name",
        ])

        self.guild_messages = prom.Counter("messages_sent", "What messages have been sent and by who", [
            "guild_id"
        ])


        self.user_message_raw_count = prom.Counter("user_message_raw_count", "Raw count of how many messages we have seen from users")
        self.bot_message_raw_count = prom.Counter("bot_message_raw_count",
                                                  "Raw count of how many messages we have seen from bots")
        self.own_message_raw_count = prom.Counter("own_message_raw_count", "Raw count of how many messages GearBot has send")

        self.bot_guilds = prom.Gauge("bot_guilds", "How many guilds the bot is in")
        self.bot_guilds.set_function(lambda:  len(bot.guilds))

        self.bot_users = prom.Gauge("bot_users", "How many users the bot can see")
        self.bot_users.set_function(lambda : sum(len(g.members) for g in bot.guilds))

        self.bot_users_unique = prom.Gauge("bot_users_unique", "How many unique users the bot can see")
        self.bot_users_unique.set_function(lambda : len(bot.users))

        self.bot_event_counts = prom.Counter("bot_event_counts", "How much each event occurred", ["event_name"])

        self.bot_latency = prom.Gauge("bot_latency", "Current bot latency")
        self.bot_latency.set_function(lambda : bot.latency)

        bot.metrics_reg.register(self.command_counter)
        bot.metrics_reg.register(self.guild_messages)
        bot.metrics_reg.register(self.user_message_raw_count)
        bot.metrics_reg.register(self.bot_message_raw_count)
        bot.metrics_reg.register(self.bot_guilds)
        bot.metrics_reg.register(self.bot_users)
        bot.metrics_reg.register(self.bot_users_unique)
        bot.metrics_reg.register(self.bot_event_counts)
        bot.metrics_reg.register(self.own_message_raw_count)
        bot.metrics_reg.register(self.bot_latency)