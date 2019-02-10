# Basic
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Shows some runtime info like uptime, messages seen and link to support server. |
|about|public (0)| |
| | |Example: ``!about``|
| | | Random cats! |
|cat|public (0)| |
| | |Example: ``!cat``|
| | | Random decision making. |
|coinflip|public (0)| |
| | |Example: ``!coinflip [thing]``|
| | | Random dogs! |
|dog|public (0)| |
| | |Example: ``!dog``|
| | | Lists all commands, the commands from a cog or info about a command. |
|help|public (0)| |
| | |Example: ``!help [query]``|
| | | Jumbo emoji. |
|jumbo|public (0)| |
| | |Example: ``!jumbo <emojis>``|
| | | See if the bot is still online. |
|ping|public (0)| |
| | |Example: ``!ping``|
| | | Quotes the requested message. |
|quote|public (0)| |
| | |Example: ``!quote <message>``|
| | | Shows self-assignable roles or assigns/removes one. |
|self_role|public (0)| |
| | |Example: ``![self_roleǀselfroleǀself_rolesǀselfroles] [role]``|
| | | Prints out any Discord user IDs found in the specified text. |
|uid|public (0)| |
| | |Example: ``!uid <text>``|


# CustCommands
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Lists all custom commands for this server, also the base command to making, updating and removing them. |
|commands|public (0)| |
| | |Example: ``![commandsǀcommand]``|
| | | Create a new command. |
|commands create|mod (2)| |
| | |Example: ``!commands [createǀnewǀadd] <trigger> [reply]``|
| | | Removes a custom command. |
|commands remove|mod (2)| |
| | |Example: ``!commands remove <trigger>``|
| | | Sets a new reply for the specified command. |
|commands update|mod (2)| |
| | |Example: ``!commands update <trigger> [reply]``|


# Emoji
Default permission requirement: admin (3)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Base command for managing emoji. |
|emoji|admin (3)| |
| | |Example: ``![emojiǀemote]``|
| | |  |
|emoji list|admin (3)| |
| | |Example: ``!emoji list``|
| | |  |
|emoji info|admin (3)| |
| | |Example: ``!emoji info <emoji>``|
| | | Uploads a new emoji. |
|emoji add|admin (3)| |
| | |Example: ``!emoji [addǀuploadǀcreate] <name> [roles]``|
| | | Changes the emoji name. |
|emoji update|admin (3)| |
| | |Example: ``!emoji [updateǀchangeǀrenameǀredefine] <emote> <new_name>``|
| | | Removes an emoji. |
|emoji delete|admin (3)| |
| | |Example: ``!emoji [deleteǀremoveǀnukeǀrmvǀdelǀ👋ǀ🗑] <emote>``|
| | | Manage the role requirements to use emoji. |
|emoji roles|admin (3)| |
| | |Example: ``!emoji [rolesǀrole]``|
| | |  |
|emoji roles add|admin (3)| |
| | |Example: ``!emoji roles add <emote> [roles]``|
| | |  |
|emoji roles remove|admin (3)| |
| | |Example: ``!emoji roles remove <emote> <roles>``|


# Infractions
Default permission requirement: mod (2)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Base infractions command, see the sub-commands for details. |
|inf|mod (2)| |
| | |Example: ``![infǀinfractionǀinfractions]``|
| | | Shows all infractions given by or to a given user. |
|inf search|mod (2)| |
| | |Example: ``!inf search [fields] [query]``|
| | | Updates an infraction. |
|inf update|mod (2)| |
| | |Example: ``!inf update <infraction> <reason>``|
| | | Deletes an infraction. This can not be undone! |
|inf delete|owner only (5)| |
| | |Example: ``!inf [deleteǀdelǀremove] <infraction>``|
| | | Claim responsibility for an infraction as moderator. |
|inf claim|mod (2)| |
| | |Example: ``!inf claim <infraction>``|
| | | Shows details on a specific infraction. |
|inf info|mod (2)| |
| | |Example: ``!inf [infoǀdetails] <infraction>``|
| | | Adds a new warning, the user is not informed of this. |
|warn|mod (2)| |
| | |Example: ``!warn <member> <reason>``|


# Minecraft
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Base command to pull mod info from Curseforge, still WIP. |
|cf|public (0)| |
| | |Example: ``!cf``|
| | |  |
|cf info|public (0)| |
| | |Example: ``!cf info <project_name>``|


# Moderation
Default permission requirement: mod (2)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Base command for archiving, use the sub-commands to actually make archives. |
|archive|mod (2)| |
| | |Example: ``!archive``|
| | | Archive messages from a channel. |
|archive channel|mod (2)| |
| | |Example: ``!archive channel [channel] [amount=100]``|
| | | Archive messages from a user. |
|archive user|mod (2)| |
| | |Example: ``!archive user <user> [amount=100]``|
| | | Bans a user from the server. |
|ban|mod (2)| |
| | |Example: ``![banǀ🚪] <user> [reason]``|
| | | Beans a user on the server. |
|bean|mod (2)| |
| | |Example: ``!bean <user> [reason]``|
| | | Gets out the broom to clean whatever mess needs cleaning. |
|clean|mod (2)| |
| | |Example: ``!clean``|
| | | Removes messages by one or more users. |
|clean user|mod (2)| |
| | |Example: ``!clean user <users> [amount=50]``|
| | | Removes messages sent by any bot. |
|clean bots|mod (2)| |
| | |Example: ``!clean bots [amount=50]``|
| | | Just clean everything. |
|clean all|mod (2)| |
| | |Example: ``!clean all <amount>``|
| | | Cleans all messages send in the last x time (5 m for example). |
|clean last|mod (2)| |
| | |Example: ``!clean last <duration> [excess]``|
| | | Cleans until the given message (message is also removed). |
|clean until|mod (2)| |
| | |Example: ``!clean until <message>``|
| | | Cleans both messages given and everything in between. |
|clean between|mod (2)| |
| | |Example: ``!clean between <start> <end>``|
| | | Removes messages by one or more users in all channels. |
|clean everywhere|mod (2)| |
| | |Example: ``!clean everywhere <users> [amount=50]``|
| | | Same as a regular ban, but removes one day of messages by default, can go up to 7. |
|cleanban|mod (2)| |
| | |Example: ``![cleanbanǀclean_ban] <user> [days=1] [reason]``|
| | | Bans a user even if they are not in the server. |
|forceban|mod (2)| |
| | |Example: ``!forceban <user> [reason]``|
| | | Kicks a user from the server. |
|kick|mod (2)| |
| | |Example: ``![kickǀ👢] <user> [reason]``|
| | | Bans multiple users with the same reason. |
|mban|mod (2)| |
| | |Example: ``!mban <targets> [reason]``|
| | | Kicks multiple users with the same reason. |
|mkick|mod (2)| |
| | |Example: ``!mkick <targets> [reason]``|
| | | Temporarily mutes someone. |
|mute|mod (2)| |
| | |Example: ``!mute <target> <duration> [reason]``|
| | | Purges up to 1000 messages in this channel. |
|purge|mod (2)| |
| | |Example: ``!purge <count>``|
| | | Adds or removes roles from members. |
|role|mod (2)| |
| | |Example: ``!role``|
| | | Adds a role to someone. |
|role add|mod (2)| |
| | |Example: ``!role add <user> <role>``|
| | | Removes a role from someone. |
|role remove|mod (2)| |
| | |Example: ``!role [removeǀrmv] <user> <role>``|
| | | Prints a list of all roles in the server, possible modes are alphabetic or hierarchy (default). |
|roles|mod (2)| |
| | |Example: ``!roles [mode=hierarchy]``|
| | | Shows when the last message by the user was logged. |
|seen|mod (2)| |
| | |Example: ``!seen <user>``|
| | | Shows information about the current server. |
|serverinfo|mod (2)| |
| | |Example: ``![serverinfoǀserver] [guild]``|
| | | Soft bans a user from the server (ban, removes last day of messages and unbans). |
|softban|mod (2)| |
| | |Example: ``!softban <user> [reason]``|
| | | Temporarily bans someone from the server (regardless on if they are on the server atm or not). |
|tempban|mod (2)| |
| | |Example: ``!tempban <user> <duration> [reason]``|
| | | Unbans a user from the server. |
|unban|mod (2)| |
| | |Example: ``!unban <member> [reason]``|
| | | Lifts a mute. |
|unmute|mod (2)| |
| | |Example: ``!unmute <target> [reason]``|
| | | Shows information about the chosen user. |
|userinfo|mod (2)| |
| | |Example: ``![userinfoǀinfo] [user]``|


# Reminders
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Base command for reminders. |
|remind|public (0)| |
| | |Example: ``![remindǀrǀreminder]``|
| | | Schedule to be reminded about something. |
|remind me|public (0)| |
| | |Example: ``!remind [meǀaddǀmǀa] <duration> <reminder>``|


# Serveradmin
Default permission requirement: admin (3)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
| | | Configure server specific settings. |
|configure|admin (3)| |
| | |Example: ``![configureǀconfigǀcfg]``|
| | | Sets or shows the server prefix. |
|configure prefix|admin (3)| |
| | |Example: ``!configure prefix [new_prefix]``|
| | | Show or configure server admin roles. |
|configure admin_roles|admin (3)| |
| | |Example: ``!configure [admin_rolesǀadminroles]``|
| | |  |
|configure admin_roles add|admin (3)| |
| | |Example: ``!configure admin_roles add <role>``|
| | |  |
|configure admin_roles remove|admin (3)| |
| | |Example: ``!configure admin_roles remove <role>``|
| | | Show or configure server mod roles. |
|configure mod_roles|admin (3)| |
| | |Example: ``!configure [mod_rolesǀmodroles]``|
| | |  |
|configure mod_roles add|admin (3)| |
| | |Example: ``!configure mod_roles add <role>``|
| | |  |
|configure mod_roles remove|admin (3)| |
| | |Example: ``!configure mod_roles remove <role>``|
| | | Show or configure server trusted roles. |
|configure trusted_roles|admin (3)| |
| | |Example: ``!configure [trusted_rolesǀtrustedroles]``|
| | |  |
|configure trusted_roles add|admin (3)| |
| | |Example: ``!configure trusted_roles add <role>``|
| | |  |
|configure trusted_roles remove|admin (3)| |
| | |Example: ``!configure trusted_roles remove <role>``|
| | | Sets what role to use for muting people. |
|configure mute_role|admin (3)| |
| | |Example: ``!configure [mute_roleǀmuterole] <role>``|
| | | Allows adding/removing roles from the self-assignable list. |
|configure self_roles|admin (3)| |
| | |Example: ``!configure [self_rolesǀselfroleǀself_role]``|
| | |  |
|configure self_roles add|admin (3)| |
| | |Example: ``!configure self_roles add <role>``|
| | |  |
|configure self_roles remove|admin (3)| |
| | |Example: ``!configure self_roles remove <role>``|
| | | Allows adding/removing servers from the invite whitelist, only enforced when there are servers on the list. |
|configure invite_whitelist|admin (3)| |
| | |Example: ``!configure invite_whitelist``|
| | |  |
|configure invite_whitelist add|admin (3)| |
| | |Example: ``!configure invite_whitelist add <server>``|
| | |  |
|configure invite_whitelist remove|admin (3)| |
| | |Example: ``!configure invite_whitelist remove <server>``|
| | | Configures users to ignore for edit/delete logs (like bots spamming the logs with edits). |
|configure ignored_users|admin (3)| |
| | |Example: ``!configure [ignored_usersǀignoredUsers]``|
| | |  |
|configure ignored_users add|admin (3)| |
| | |Example: ``!configure ignored_users add <user>``|
| | |  |
|configure ignored_users remove|admin (3)| |
| | |Example: ``!configure ignored_users remove <user>``|
| | | Configure permission overrides for cogs. |
|configure cog_overrides|admin (3)| |
| | |Example: ``!configure cog_overrides``|
| | |  |
|configure cog_overrides add|admin (3)| |
| | |Example: ``!configure cog_overrides add <cog> <perm_lvl>``|
| | |  |
|configure cog_overrides remove|admin (3)| |
| | |Example: ``!configure cog_overrides remove <cog>``|
| | | Configure permission overrides for individual commands, this ignores any overrides. |
|configure command_overrides|admin (3)| |
| | |Example: ``!configure command_overrides``|
| | |  |
|configure command_overrides set|admin (3)| |
| | |Example: ``!configure command_overrides [setǀadd] <command> <perm_lvl>``|
| | |  |
|configure command_overrides remove|admin (3)| |
| | |Example: ``!configure command_overrides remove <command>``|
| | | Configure if a message should be shown if someone tries to run a command they do not have access to. |
|configure perm_denied_message|admin (3)| |
| | |Example: ``!configure perm_denied_message <value>``|
| | | Sets the language to use on this server. |
|configure language|admin (3)| |
| | |Example: ``!configure language [lang_code]``|
| | | Allows adding/removing people to lvl 4 permission lvl for a command. |
|configure lvl4|owner only (5)| |
| | |Example: ``!configure lvl4``|
| | |  |
|configure lvl4 add|owner only (5)| |
| | |Example: ``!configure lvl4 add <command> <person>``|
| | |  |
|configure lvl4 remove|owner only (5)| |
| | |Example: ``!configure lvl4 remove <command> <person>``|
| | |  |
|configure logging|admin (3)| |
| | |Example: ``!configure logging``|
| | |  |
|configure logging add|admin (3)| |
| | |Example: ``!configure logging add <channel> <types>``|
| | |  |
|configure logging remove|admin (3)| |
| | |Example: ``!configure logging remove <cid> <types>``|
| | |  |
|configure logging dash|admin (3)| |
| | |Example: ``!configure logging dash``|
| | |  |
|configure features|admin (3)| |
| | |Example: ``!configure features``|
| | |  |
|configure features enable|admin (3)| |
| | |Example: ``!configure features enable <types>``|
| | |  |
|configure features disable|admin (3)| |
| | |Example: ``!configure features disable <types>``|
| | | Configures ignored channels |
|configure ignored_channels|admin (3)| |
| | |Example: ``!configure ignored_channels``|
| | | Configures channels to ignore for logging channel changes. |
|configure ignored_channels changes|admin (3)| |
| | |Example: ``!configure ignored_channels changes``|
| | | Adds a channel to the ignored list |
|configure ignored_channels changes add|admin (3)| |
| | |Example: ``!configure ignored_channels changes add <channel>``|
| | | Removes a channel from the ignored list again. |
|configure ignored_channels changes remove|admin (3)| |
| | |Example: ``!configure ignored_channels changes remove <channel>``|
| | | Shows the list of channels currently on the ignore list. |
|configure ignored_channels changes list|admin (3)| |
| | |Example: ``!configure ignored_channels changes list``|
| | | Configures channel to ignore for edit and delete logs. |
|configure ignored_channels edits|admin (3)| |
| | |Example: ``!configure ignored_channels [editsǀedit]``|
| | | Adds a channel to the ignored list. |
|configure ignored_channels edits add|admin (3)| |
| | |Example: ``!configure ignored_channels edits add <channel>``|
| | | Removes a channel from the ignored list again. |
|configure ignored_channels edits remove|admin (3)| |
| | |Example: ``!configure ignored_channels edits remove <channel>``|
| | | Shows the list of channels currently on the ignore list. |
|configure ignored_channels edits list|admin (3)| |
| | |Example: ``!configure ignored_channels edits list``|
| | | Configure warning behaviour for DMs (off by default). |
|configure dm_on_warn|admin (3)| |
| | |Example: ``!configure dm_on_warn <value>``|
| | |  |
|configure log_embeds|admin (3)| |
| | |Example: ``!configure log_embeds <value>``|
| | |  |
|configure blacklist|admin (3)| |
| | |Example: ``!configure blacklist``|
| | |  |
|configure blacklist add|admin (3)| |
| | |Example: ``!configure blacklist add <word>``|
| | |  |
|configure blacklist remove|admin (3)| |
| | |Example: ``!configure blacklist remove <word>``|
| | | Configures or shows the managed roles config list. |
|configure role_list|admin (3)| |
| | |Example: ``!configure role_list``|
| | | Adds a role to the configuration list. |
|configure role_list add|admin (3)| |
| | |Example: ``!configure role_list add <role>``|
| | | Removes a role from the configuration list. |
|configure role_list remove|admin (3)| |
| | |Example: ``!configure role_list [removeǀrmv] <role>``|
| | | Sets if the list is a whitelist or blacklist. |
|configure role_list mode|admin (3)| |
| | |Example: ``!configure role_list mode <mode>``|
| | | Base command for disabling features. |
|disable|admin (3)| |
| | |Example: ``!disable``|
| | | Disable the mute feature. |
|disable mute|admin (3)| |
| | |Example: ``!disable mute``|


