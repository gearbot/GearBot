import hashlib
import os
import platform
import re

import discord
from discord.ext.commands import GroupMixin

from Util import Configuration, Utils, Pages, GearbotLogging, Emoji, Permissioncheckers, Translator

image_pattern = re.compile("(?:!\[)([A-z ]+)(?:\]\()(?:\.*/*)(.*)(?:\))(.*)")

async def update_docs(ctx):
    if Configuration.get_master_var("DOCS"):
        await ctx.send(f"{Emoji.get_chat_emoji('REFRESH')} Updating website")
        await sync_guides(ctx.bot)
        generate_command_list(ctx.bot)
        await update_site(ctx.bot)
        await ctx.send(content=f"{Emoji.get_chat_emoji('YES')} Website updated, see logs for details")

async def sync_guides(bot):
    category = bot.get_channel(Configuration.get_master_var("GUIDES"))
    if category is not None:
        guide_hashes = Configuration.get_persistent_var("guide_hashes", {})
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
        Configuration.set_persistent_var("guide_hashes", guide_hashes)

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
            message = f"{Emoji.get_chat_emoji('YES')} Website updated\n```yaml\n{output.decode('utf-8')}``` ```yaml\n{error.decode('utf-8')}```"
        else:
            message = f"{Emoji.get_chat_emoji('NO')} Website update failed with code {code}\nScript output:```yaml\n{output.decode('utf-8')} ``` Script error output:```yaml\n{error.decode('utf-8')} ```"
            await GearbotLogging.message_owner(bot, message)
        await log_message.edit(content=message)

def generate_command_list(bot):
    page = ""
    handled = set()
    for cog in sorted(bot.cogs):
        cogo = bot.get_cog(cog)
        if cogo.permissions is not None:
            perm_lvl = cogo.permissions["required"]
            page += f"# {cog}\nDefault permission requirement: {Translator.translate(f'perm_lvl_{perm_lvl}', None)} ({perm_lvl})\n\n|   Command | Default lvl | Explanation |\n| ----------------|--------|-------------------------------------------------------|\n"
            for command in sorted(cogo.get_commands(), key= lambda c:c.qualified_name):
                if command.qualified_name not in handled:
                    page += gen_command_listing(command)
                    handled.add(command.qualified_name)
            page += "\n\n"
    with open("web/src/docs/commands.md", "w", encoding="utf-8") as file:
        file.write(page)

def gen_command_listing(command):
    try:
        perm_lvl = Permissioncheckers.get_perm_dict(command.qualified_name.split(' '), command.instance.permissions)['required']
        listing = f"| | | {Translator.translate(command.short_doc, None)} |\n"
        listing += f"|{command.qualified_name}|{Translator.translate(f'perm_lvl_{perm_lvl}', None)} ({perm_lvl})| |\n"
        signature = str(command.signature).replace("|", "ǀ")
        listing += f"| | |Example: ``!{signature}``|\n"
    except Exception as ex:
        GearbotLogging.error(command.qualified_name)
        raise ex
    else:
        if isinstance(command, GroupMixin) and hasattr(command, "all_commands"):
            handled = set()
            for c in command.all_commands.values():
                if c.qualified_name not in handled:
                    listing += gen_command_listing(c)
                    handled.add(c.qualified_name)
        return listing
