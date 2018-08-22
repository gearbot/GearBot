import hashlib
import os
import platform
import re

import discord

from Util import Configuration, Utils, Pages, GearbotLogging, Emoji

image_pattern = re.compile("(?:!\[)([A-z ]+)(?:\]\()(?:\.*/*)(.*)(?:\))(.*)")

async def update_docs(bot):
    await GearbotLogging.logToBotlog(f"{Emoji.get_chat_emoji('REFRESH')} Updating documentation")
    await sync_guides(bot)
    await update_site(bot)

async def sync_guides(bot):
    category = bot.get_channel(Configuration.getMasterConfigVar("GUIDES"))
    if category is not None:
        guide_hashes = Utils.fetchFromDisk("guide_hashes")
        for channel in category.channels:
            if isinstance(channel, discord.TextChannel):
                name = channel.name
                if os.path.isfile(f"docs/Guides/{name}.md") or os.path.isfile(f"../docs/Guides/{name}.md"):
                    GearbotLogging.info(f"Found guide {name}, verifying file hash...")
                    h = hashlib.md5(open(f"docs/Guides/{name}.md", 'rb').read()).hexdigest()
                    if not name in guide_hashes or guide_hashes[name] != h:
                        GearbotLogging.info(f"Guide {name} is outdated, updating...")
                        guide_hashes[name] = h
                        with open(f"docs/Guides/{name}.md", 'r') as file:
                            buffer = ""
                            await channel.purge()
                            for line in file.readlines():
                                while line.startswith('#'):
                                    line = line[1:]
                                match = image_pattern.search(line)
                                if match is None:
                                    buffer += f"{line}"
                                else:
                                    if buffer != "":
                                        await send_buffer(channel, buffer)
                                    await channel.send(file=discord.File(f"docs/{match.group(2)}"))
                                    buffer = match.group(3)
                            await send_buffer(channel, buffer)
            else:
                GearbotLogging.info(f"Found guide channel {name} but file for it!")
        Utils.saveToDisk("guide_hashes", guide_hashes)

async def send_buffer(channel, buffer):
    pages = Pages.paginate(buffer, max_lines=500)
    for page in pages:
        await channel.send(page)


async def update_site(bot):
    if os.path.isfile(f"./site-updater.sh") and platform.system().lower() != "windows":
        await GearbotLogging.logToBotlog(f"{Emoji.get_chat_emoji('REFRESH')} Updating website")
        output, error = await Utils.execute(["chmod +x site-updater.sh"])
        out, err = await Utils.execute(["./site-updater.sh"])
        output = f"{output.decode('utf-8')}\n{out.decode('utf-8')}"
        error = f"{error.decode('utf-8')}\n{err.decode('utf-8')}"
        GearbotLogging.info("Site update output")
        if error == "\n":
            await GearbotLogging.logToBotlog(f"{Emoji.get_chat_emoji('YES')} Website updated:```yaml\n{output}```")
        else:
            message = f"{Emoji.get_chat_emoji('NO')} Website update failed, script output:```yaml\n{output} \n``` script error output:```yaml\n{error} \n```"
            await GearbotLogging.logToBotlog(message)
            await GearbotLogging.message_owner(bot, message)