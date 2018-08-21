import hashlib
import os
import re

import discord

from Util import Configuration, Utils, Pages

image_pattern = re.compile("(?:!\[)([A-z ]+)(?:\]\()(?:\.*/*)(.*)(?:\))(.*)")

async def sync_guides(bot):
    category = bot.get_channel(Configuration.getMasterConfigVar("GUIDES"))
    if category is not None:
        guide_hashes = Utils.fetchFromDisk("guide_hashes")
        for channel in category.channels:
            if isinstance(channel, discord.TextChannel):
                name = channel.name
                if os.path.isfile(f"docs/Guides/{name}.md") or os.path.isfile(f"../docs/Guides/{name}.md"):
                    h = hashlib.md5(open(f"docs/Guides/{name}.md", 'rb').read()).hexdigest()
                    if not name in guide_hashes or guide_hashes[name] != h:
                        guide_hashes[name] = h
                        with open (f"docs/Guides/{name}.md", 'r') as file:
                            buffer = ""
                            await channel.purge()
                            for line in file.readlines():
                                while line.startswith('#'):
                                    line = line [1:]
                                match = image_pattern.search(line)
                                if match is None:
                                    buffer += f"{line}"
                                else:
                                    if buffer != "":
                                        await send_buffer(channel, buffer)
                                    await channel.send(file=discord.File(f"docs/{match.group(2)}"))
                                    buffer = match.group(3)
                            await send_buffer(channel, buffer)
        Utils.saveToDisk("guide_hashes", guide_hashes)




async def send_buffer(channel, buffer):
    pages = Pages.paginate(buffer, max_lines=500)
    for page in pages:
        await channel.send(page)