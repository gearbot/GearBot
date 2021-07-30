import collections

from discord.ext.commands import GroupMixin

from Util import Utils, Pages, Translator, Permissioncheckers, Configuration


async def command_list(bot, member, guild):
    command_tree = dict()
    longest = 0
    for cog in bot.cogs:
        commands, l = await cog_commands(bot, cog, member, guild)
        if commands is not None:
            command_tree[cog] = commands
            if l > longest:
                longest = l
    command_tree = collections.OrderedDict(sorted(command_tree.items()))


    output_tree = collections.OrderedDict()
    for cog, commands in command_tree.items():
        output = f'- {cog}\n'
        for command_name, info in commands.items():
            output += "  " + command_name + (" " * (longest - len(command_name) + 2)) + info + "\n"
        output_tree[cog] = output
    # sometimes we get a null prefix for some reason?
    prefix = Configuration.get_var(guild.id, "GENERAL", "PREFIX")
    return dict_to_pages(output_tree, f"You can get more info about a command (params and subcommands) by using '{prefix}help <command>'\nCommands followed by ↪  have subcommands")


async def cog_commands(bot, cog, member, guild):
    commands = bot.get_cog(cog).get_commands()
    if len(commands) == 0:
        return None, None
    return await gen_commands_list(bot, member, guild, commands)

async def gen_commands_list(bot, member, guild, list):
    longest = 0
    command_list = dict()
    for command in list:
        runnable = member is not None and await Permissioncheckers.check_permission(command, guild, member, bot)
        if not command.hidden and runnable:
            indicator = "\n  ↪" if isinstance(command, GroupMixin) else ""
            command_list[command.name] = Utils.trim_message(Translator.translate(command.short_doc, guild), 120) + indicator
            if len(command.name) > longest:
                longest = len(command.name)
    if len(command_list) > 0:
        return collections.OrderedDict(sorted(command_list.items())), longest
    else:
        return None, None


async def gen_cog_help(bot, cog, member, guild):
    commands, longest = await cog_commands(bot, cog, member, guild)
    output = f'- {cog}\n'
    if commands is not None:
        for command_name, info in commands.items():
            output += command_name + (" " * (longest - len(command_name) + 4)) + info + "\n"
        return Pages.paginate(output)
    else:
        return None

async def gen_command_help(bot, member, guild, command):
    signature = ""
    parent = command.parent
    while parent is not None:
        if not parent.signature or parent.invoke_without_command:
            signature = f"{parent.name} {signature}"
        else:
            signature = f"{parent.name} {parent.signature} {signature}"
        parent = parent.parent

    if len(command.aliases) > 0:
        aliases = '|'.join(command.aliases)
        signature = f"{signature} [{command.name}|{aliases}]"
    else:
        signature = f"{signature} {command.name}"
    prefix = Configuration.get_var(guild.id, "GENERAL", "PREFIX")
    usage = f"{prefix}{signature}"
    sub_info = None
    if isinstance(command, GroupMixin) and hasattr(command, "all_commands"):
        subcommands, longest = await gen_commands_list(bot, member, guild, command.all_commands.values())
        if subcommands is not None:
            sub_info = "\nSub commands:\n"
            for command_name, info in subcommands.items():
                sub_info += "  " + command_name + (" " * (longest - len(command_name) + 4)) + info + "\n"
            sub_info += Translator.translate('help_footer', guild, prefix=prefix, signature=signature)

    return Pages.paginate(f"{usage}\n\n{Translator.translate(command.help, guild)}\n{'' if sub_info is None else sub_info}".replace(bot.user.mention, f"@{bot.user.name}"))

def dict_to_pages(dict, suffix=""):
    pages = []
    output = ""
    for out in dict.values():
        if len(output) + len(out) > 1000:
            pages.append(f"{output}\n{suffix}")
            output = out
        else:
            if output == "":
                output = Utils.trim_message(out, 2000 - 15 - len(suffix))
            else:
                output += out + "\n"
    pages.append(f"{output}\n{suffix}")
    # if some page does end up over 2k, split it
    real_pages = []
    for p in pages:
        for page in Pages.paginate(p, max_lines=100):
            real_pages.append(page)
    return real_pages