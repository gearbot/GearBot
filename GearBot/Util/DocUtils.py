import re

from Util import Configuration, Pages, GearbotLogging, Emoji, Permissioncheckers, Translator

image_pattern = re.compile("(?:!\[)([A-z ]+)(?:\]\()(?:\.*/*)(.*)(?:\))(.*)")

async def update_docs(ctx):
    if Configuration.get_master_var("DOCS"):
        await ctx.send(f"{Emoji.get_chat_emoji('REFRESH')} Updating website")
        generate_command_list(ctx.bot)
        await ctx.send(content=f"{Emoji.get_chat_emoji('YES')} Website updated, see logs for details")

async def send_buffer(channel, buffer):
    pages = Pages.paginate(buffer, max_lines=500)
    for page in pages:
        await channel.send(page)

def generate_command_list(bot):
    for code in Translator.LANGS.keys():
        page = ""
        handled = set()
        for cog in sorted(bot.cogs):
            cogo = bot.get_cog(cog)
            if cogo.permissions is not None:
                perm_lvl = cogo.permissions["required"]
                default = Translator.translate_by_code("help_page_default_perm")
                plvl = Translator.translate_by_code(f'perm_lvl_{perm_lvl}', code)
                c = Translator.translate_by_code("command", code)
                default_lvl = Translator.translate_by_code("help_page_default_lvl", code)
                explanation = Translator.translate_by_code("explanation", code)
                page += f"# {cog}\n{default}: {plvl} ({perm_lvl})\n\n|   {c} | {default_lvl} | {explanation} |\n| ----------------|--------|-------------------------------------------------------|\n"
                for command in sorted([c for c in cogo.walk_commands()], key= lambda c:c.qualified_name):
                    if command.qualified_name not in handled:
                        page += gen_command_listing(cogo, command, code)
                        handled.add(command.qualified_name)
                page += "\n\n"
        with open(Configuration.get_master_var("DOC_LOCATION", "WEBSITE_ROOT") +  f"/pages/03.docs/01.Commands/commands.{code}.md", "w", encoding="utf-8") as file:
            file.write(page)

def gen_command_listing(cog, command, code):
    try:
        perm_lvl = Permissioncheckers.get_perm_dict(command.qualified_name.split(' '), cog.permissions)['required']
        listing = f"| | | {Translator.translate(command.short_doc, None)} |\n"
        listing += f"|{command.qualified_name}|{Translator.translate(f'perm_lvl_{perm_lvl}', None)} ({perm_lvl})| |\n"
        signature = str(command.signature).replace("|", "ǀ")
        listing += f"| | |{Translator.translate_by_code('example', code)}: ``!{signature}``|\n"
    except Exception as ex:
        GearbotLogging.error(command.qualified_name)
        raise ex
    return listing
