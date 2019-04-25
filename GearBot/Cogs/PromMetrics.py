import prometheus_client as prom
from prometheus_client.registry import CollectorRegistry


class PromMetrics():
    def __init__(self):
        self.metrics_reg = CollectorRegistry()

        self.command_counter = prom.Counter("commands_ran", "How many times commands were ran and who ran them", [
            "command_name",
            "guild_id"
        ])

        self.guild_messages = prom.Counter("messages_sent", "What messages have been sent and by who", [
            "guild_id"
        ])

        self.messages_to_length = prom.Counter("messages_to_length", "Keeps track of what messages were what length", [
            "length"
        ])

        self.user_message_raw_count = prom.Counter("user_message_raw_count", "Raw count of how many messages we have seen from users")
        self.bot_message_raw_count = prom.Counter("bot_message_raw_count", "Raw count of how many messages we have seen from bots")

        self.metrics_reg.register(self.command_counter)
        self.metrics_reg.register(self.guild_messages)
        self.metrics_reg.register(self.messages_to_length)
        self.metrics_reg.register(self.user_message_raw_count)
        self.metrics_reg.register(self.bot_message_raw_count)