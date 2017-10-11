import discord

from commands.RoleCommands import RoleCommand


class Roles(RoleCommand):
    """Role listing"""

    def __init__(self) -> None:
        super().__init__()
        self.extraHelp["info"] = "This command will print a list of all roles on this server and their ID's"

    async def execute(self, client: discord.Client, channel: discord.Channel, user: discord.user.User, params) -> None:
        roles = ""
        ids = ""
        for role in channel.server.roles:
            roles += f"<@&{role.id}>\n\n"
            ids += role.id + "\n\n"
        embed = discord.Embed(title=channel.server.name + " roles", color=0x54d5ff)
        embed.add_field(name="\u200b", value=roles, inline=True)
        embed.add_field(name="\u200b", value=ids, inline=True)
        await client.send_message(channel, embed=embed)

