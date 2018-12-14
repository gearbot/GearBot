import hashlib
import os
import platform
import re

import discord
from discord.ext.commands import GroupMixin

from Util import Configuration, Utils, Pages, GearbotLogging, Emoji, Permissioncheckers, Translator

image_pattern = re.compile("(?:!\[)([A-z ]+)(?:\]\()(?:\.*/*)(.*)(?:\))(.*)")

async def update_docs(bot):
    if Configuration.get_master_var("DOCS"):
        message = await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('REFRESH')} Updating documentation")
        await sync_guides(bot)
        generate_command_list(bot)
        await update_site(bot)
        await message.edit(content=f"{Emoji.get_chat_emoji('YES')} Documentation updated")

async def sync_guides(bot):
    category = bot.get_channel(Configuration.get_master_var("GUIDES"))
    if category is not None:
        guide_hashes = Utils.fetch_from_disk("guide_hashes")
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
        log_message = await GearbotLogging.bot_log(f"{Emoji.get_chat_emoji('REFRESH')} Updating website")
        code, output, error = await Utils.execute(["chmod +x site-updater.sh && ./site-updater.sh"])
        GearbotLogging.info("Site update output")
        if code is 0:
            message = f"{Emoji.get_chat_emoji('YES')} Website updated:```yaml\n{output.decode('utf-8')}\n{error.decode('utf-8')}```"
        else:
            message = f"{Emoji.get_chat_emoji('NO')} Website update failed with code {code}\nScript output:```yaml\n{output.decode('utf-8')} ``` Script error output:```yaml\n{error.decode('utf-8')} ```"
            await GearbotLogging.message_owner(bot, message)
        await log_message.edit(content=message)

def generate_command_list(bot):
    excluded = [
        "Admin", "BCVersionChecker", "Censor", "ModLog", "PageHandler", "Reload", "DMMessages"
    ]
    page = ""
    for cog in bot.cogs:
        if cog not in excluded:
            page += f"#{cog}\n|   Command | Default lvl | Explanation |\n| ----------------|--------|-------------------------------------------------------|\n"
            for command in bot.get_cog_commands(cog):
                page += gen_command_listing(command)
            page += "\n\n"
    with open("docs/commands.md", "w") as file:
        file.write(page)

def gen_command_listing(command):
    try:
        listing = f"|{command.qualified_name}|{Permissioncheckers.get_perm_dict(command.qualified_name.split(' '), command.instance.permissions)['required']}|{Translator.translate(command.short_doc, None)}|\n"
    except Exception as ex:
        GearbotLogging.error(command.qualified_name)
        raise ex
    else:
        if isinstance(command, GroupMixin) and hasattr(command, "all_commands"):
            for c in command.all_commands.values():
                listing += gen_command_listing(c)
        return listing
