import discord

from commands.RoleCommands import RoleCommand


class Clean(RoleCommand):
    """Remove messages from a user"""


    def __init__(self):
        super().__init__()
        self.extraHelp["info"] = "Remove messages from a user with the specified ID"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        if len(params) != 1:
            await client.send_message("Invalid params")
            return
        await client.send_message(channel, "Commencing cleanup")
        async for log in client.logs_from(channel, limit=250):
            if log.author.id == params[0]:
                await client.delete_message(log)
        await client.send_message(channel, "Cleanup complete")