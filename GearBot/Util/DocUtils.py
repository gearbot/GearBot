import os
import re

from Util import Configuration, Pages, GearbotLogging, Permissioncheckers, Translator, Utils

image_pattern = re.compile("(?:!\[)([A-z ]+)(?:\]\()(?:\.*/*)(.*)(?:\))(.*)")

async def send_buffer(channel, buffer):
    pages = Pages.paginate(buffer, max_lines=500)
    for page in pages:
        await channel.send(page)

async def generate_command_list(bot, message):
    ctx = await bot.get_context(message)
    ctx.prefix = "!"
    bot.help_command.context = ctx
    for code in Translator.LANGS.keys():
        page = ""
        handled = set()
        for cog in sorted(bot.cogs):
            cogo = bot.get_cog(cog)
            if cogo.permissions is not None:
                perm_lvl = cogo.permissions["required"]
                default = Translator.translate_by_code("help_page_default_perm", code)
                plvl = Translator.translate_by_code(f'perm_lvl_{perm_lvl}', code)
                c = Translator.translate_by_code("command", code)
                default_lvl = Translator.translate_by_code("help_page_default_lvl", code)
                explanation = Translator.translate_by_code("explanation", code)
                page += f"# {cog}\n{default}: {plvl} ({perm_lvl})\n\n|   {c} | {default_lvl} | {explanation} |\n| ----------------|--------|-------------------------------------------------------|\n"
                for command in sorted([c for c in cogo.walk_commands()], key= lambda c:c.qualified_name):
                    if command.qualified_name not in handled:
                        page += gen_command_listing(bot, cogo, command, code)
                        handled.add(command.qualified_name)
                page += "\n\n"
        folder = Configuration.get_master_var("WEBSITE_ROOT", "") +  f"/pages/03.docs/01.commands"
        if not os.path.exists(folder):
            os.makedirs(folder)
        with open(f"{folder}/doc.{code}.md", "w", encoding="utf-8") as file:
            file.write(page)

def gen_command_listing(bot, cog, command, code):
    try:
        perm_lvl = Permissioncheckers.get_perm_dict(command.qualified_name.split(' '), cog.permissions)['required']
        listing = f"| | | {Translator.translate_by_code(command.short_doc, code)} |\n"
        listing += f"|{command.qualified_name}|{Translator.translate_by_code(f'perm_lvl_{perm_lvl}', code)} ({perm_lvl})| |\n"
        signature = bot.help_command.get_command_signature(command).replace("|", "ǀ")
        listing += f"| | |{Translator.translate_by_code('example', code)}: ``{signature}``|\n"
    except Exception as ex:
        GearbotLogging.error(command.qualified_name)
        raise ex
    return listing



async def generate_command_list2(bot, message):
    ctx = await bot.get_context(message)
    ctx.prefix = "!"
    bot.help_command.context = ctx
    # for code in Translator.LANGS.keys():
    out = dict()
    handled = set()
    for cog in sorted(bot.cogs):
        cog_commands = dict()
        cogo = bot.get_cog(cog)
        if cogo.permissions is not None:
            for command in sorted([c for c in cogo.walk_commands()], key= lambda c:c.qualified_name):
                if command.qualified_name not in handled:
                    location = cog_commands
                    for c in command.full_parent_name.split(' '):
                        if c == '':
                            break
                        location = location[c]["subcommands"]
                    location[command.name] = gen_command_listing2(bot, cogo, command)
                    handled.add(command.qualified_name)
        if len(cog_commands) > 0:
            out[cog] = cog_commands
    Utils.save_to_disk("temp", out)

def gen_command_listing2(bot, cog, command):
    command_listing = dict()
    try:
        perm_lvl = Permissioncheckers.get_perm_dict(command.qualified_name.split(' '), cog.permissions)['required']
        command_listing["commandlevel"] = perm_lvl
        command_listing["description"] = command.short_doc
        command_listing["aliases"] = command.aliases
        example = bot.help_command.get_command_signature(command).strip()
        parts = str(example).split(' ')
        parts[0] = ''.join(parts[0][1:])
        for i in range(0, len(parts)):
            if "[" == parts[i][0] and "|" in parts[i]:
                parts[i] = ''.join(parts[i].split('|')[0][1:])
        command_listing["example"] = '!' + ' '.join(parts)
        command_listing["subcommands"] = {}
        return command_listing
    except Exception as ex:
        GearbotLogging.error(command.qualified_name)
        raise ex
