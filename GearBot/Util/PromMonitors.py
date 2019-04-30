import prometheus_client as prom

class PromMonitors:
    def __init__(self, bot) -> None:
        self.command_counter = prom.Counter("commands_ran", "How many times commands were ran and who ran them", [
            "command_name",
            "guild_id"
        ])

        self.guild_messages = prom.Counter("messages_sent", "What messages have been sent and by who", [
            "guild_id"
        ])

        self.messages_to_length = prom.Histogram("messages_to_length", "Keeps track of what messages were what length")

        self.user_message_raw_count = prom.Counter("user_message_raw_count", "Raw count of how many messages we have seen from users")
        self.bot_message_raw_count = prom.Counter("bot_message_raw_count",
                                                  "Raw count of how many messages we have seen from bots")

        self.bot_guilds = prom.Gauge("bot_guilds", "How many guilds the bot is in")
        self.bot_guilds.set_function(lambda:  len(bot.guilds))

        self.bot_users = prom.Gauge("bot_users", "How many users the bot can see")
        self.bot_users.set_function(lambda : sum(len(g.members) for g in bot.guilds))

        self.bot_users_unique = prom.Gauge("bot_users_unique", "How many unique users the bot can see")
        self.bot_users_unique.set_function(lambda : len(bot.users))

        self.bot_event_progress = prom.Gauge("bot_event_progress", "How many events are being processed", ["event_name"])
        self.bot_event_timing = prom.Histogram("bot_event_timing", "How long events took to process", ["event_name"])
        self.bot_event_counts = prom.Gauge("bot_event_counts", "How much each event occurred", ["event_name"])
        self.bot_command_timing = prom.Histogram("bot_command_timing", "How long commands took to run", ["command_name"])

        bot.metrics_reg.register(self.command_counter)
        bot.metrics_reg.register(self.guild_messages)
        bot.metrics_reg.register(self.messages_to_length)
        bot.metrics_reg.register(self.user_message_raw_count)
        bot.metrics_reg.register(self.bot_message_raw_count)
        bot.metrics_reg.register(self.bot_guilds)
        bot.metrics_reg.register(self.bot_users)
        bot.metrics_reg.register(self.bot_users_unique)
        bot.metrics_reg.register(self.bot_event_progress)
        bot.metrics_reg.register(self.bot_event_timing)
        bot.metrics_reg.register(self.bot_event_counts)
        bot.metrics_reg.register(self.bot_command_timing)