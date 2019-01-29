#Basic
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|about|0|Shows some runtime info like uptime, messages seen and link to support server.|
| | |Example: ``!about``|
|cat|0|Random cats!|
| | |Example: ``!cat``|
|coinflip|0|Random decision making.|
| | |Example: ``!coinflip [thing]``|
|dog|0|Random dogs!|
| | |Example: ``!dog``|
|help|0|Lists all commands, the commands from a cog or info about a command.|
| | |Example: ``!help [query]``|
|jumbo|0|Jumbo emoji|
| | |Example: ``!jumbo <emojis>``|
|ping|0|See if the bot is still online.|
| | |Example: ``!ping``|
|quote|0|Quotes the requested message.|
| | |Example: ``!quote <message>``|
|self_role|0|Shows self-assignable roles or assigns/removes one.|
| | |Example: ``![self_role|selfrole|self_roles|selfroles] [role]``|
|uid|0|Prints out any discord user ids found in the specified text|
| | |Example: ``!uid <text>``|


#CustCommands
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|commands|0|Lists all custom commands for this server, also the base command to making, updating and removing them.|
| | |Example: ``![commands|command]``|
|commands create|2|Create a new command|
| | |Example: ``!commands [create|new|add] <trigger> [reply]``|
|commands remove|2|Removes a custom command|
| | |Example: ``!commands remove <trigger>``|
|commands update|2|Sets a new reply for the specified command|
| | |Example: ``!commands update <trigger> [reply]``|


#Emoji
Default permission requirement: admin (3)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|emoji|3|Base command for managing emoji|
| | |Example: ``![emoji|emote]``|
|emoji list|3||
| | |Example: ``!emoji list``|
|emoji info|3||
| | |Example: ``!emoji info <emoji>``|
|emoji add|3|Uploads a new emoji|
| | |Example: ``!emoji [add|upload|create] <name> [roles]``|
|emoji update|3|Changes the emoji name|
| | |Example: ``!emoji [update|change|rename|redefine] <emote> <new_name>``|
|emoji delete|3|Removes an emoji|
| | |Example: ``!emoji [delete|remove|nuke|rmv|del|👋|🗑] <emote>``|
|emoji roles|3|Manage the role requirements to use emoji|
| | |Example: ``!emoji [roles|role]``|
|emoji roles add|3||
| | |Example: ``!emoji roles add <emote> [roles]``|
|emoji roles remove|3||
| | |Example: ``!emoji roles remove <emote> <roles>``|


#Infractions
Default permission requirement: mod (2)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|inf|2|Base infractions command, see the sub-commands for details.|
| | |Example: ``![inf|infraction|infractions]``|
|inf search|2|Shows all infractions given by or to a given user.|
| | |Example: ``!inf search [fields] [query]``|
|inf update|2|Updates an infraction.|
| | |Example: ``!inf update <infraction> <reason>``|
|inf delete|5|Deletes an infraction. This can not be undone!|
| | |Example: ``!inf [delete|del|remove] <infraction>``|
|inf claim|2|Claim responsibility for an infraction as moderator|
| | |Example: ``!inf claim <infraction>``|
|inf info|2|Shows details on a specific infraction|
| | |Example: ``!inf [info|details] <infraction>``|
|warn|2|Adds a new warning, the user is not informed of this.|
| | |Example: ``!warn <member> <reason>``|


#Minecraft
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|cf|0|Base command to pull mod info from curseforge, still WIP|
| | |Example: ``!cf``|
|cf info|0||
| | |Example: ``!cf info <project_name>``|


#Moderation
Default permission requirement: mod (2)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|archive|2|Base command for archiving, use the subcommands to actually make archives|
| | |Example: ``!archive``|
|archive channel|2|Archive messages from a channel|
| | |Example: ``!archive channel [channel] [amount=100]``|
|archive user|2|Archive messages from a user|
| | |Example: ``!archive user <user> [amount=100]``|
|ban|2|Bans a user from the server.|
| | |Example: ``![ban|🚪] <user> [reason]``|
|bean|2|Beans a user on the server.|
| | |Example: ``!bean <user> [reason]``|
|clean|2|Gets out the broom to clean whatever mess needs cleaning|
| | |Example: ``!clean``|
|clean user|2|Removes messages by one or more users|
| | |Example: ``!clean user <users> [amount=50]``|
|clean bots|2|Removes messages sent by any bot|
| | |Example: ``!clean bots [amount=50]``|
|clean all|2|Just clean everything|
| | |Example: ``!clean all <amount>``|
|clean last|2|Cleans all messages send in the last x time (5 m for example)|
| | |Example: ``!clean last <duration> [excess]``|
|clean until|2|Cleans until the given message (message is also removed)|
| | |Example: ``!clean until <message>``|
|clean between|2|Cleans both messages given and everything in between|
| | |Example: ``!clean between <start> <end>``|
|clean everywhere|2|Removes messages by one or more users in all channels|
| | |Example: ``!clean everywhere <users> [amount=50]``|
|cleanban|2|Same as a regular ban, but removes one day of messages by default, can go up to 7|
| | |Example: ``![cleanban|clean_ban] <user> [days=1] [reason]``|
|forceban|2|Bans a user even if they are not in the server.|
| | |Example: ``!forceban <user> [reason]``|
|kick|2|Kicks a user from the server.|
| | |Example: ``![kick|👢] <user> [reason]``|
|mban|2|Bans multiple users with the same reason|
| | |Example: ``!mban <targets> [reason]``|
|mkick|2|Kicks multiple users with the same reason|
| | |Example: ``!mkick <targets> [reason]``|
|mute|2|Temporarily mutes someone.|
| | |Example: ``!mute <target> <duration> [reason]``|
|purge|2|Purges up to 1000 messages in this channel.|
| | |Example: ``!purge <count>``|
|role|2|Adds or removes roles from members|
| | |Example: ``!role``|
|role add|2|Adds a role to someone|
| | |Example: ``!role add <user> <role>``|
|role remove|2|Removes a role from someone|
| | |Example: ``!role [remove|rmv] <user> <role>``|
|roles|2|Prints a list of all roles in the server, possible modes are alphabetic or hierarchy (default)|
| | |Example: ``!roles [mode=hierarchy]``|
|seen|2|Shows when the last message by the user was logged|
| | |Example: ``!seen <user>``|
|serverinfo|2|Shows information about the current server.|
| | |Example: ``![serverinfo|server] [guild]``|
|softban|2|Soft bans a user from the server (ban, removes last day of messages and unbans).|
| | |Example: ``!softban <user> [reason]``|
|tempban|2|Temporarily bans someone from the server (regardless on if they are on the server atm or not)|
| | |Example: ``!tempban <user> <duration> [reason]``|
|unban|2|Unbans a user from the server.|
| | |Example: ``!unban <member> [reason]``|
|unmute|2|Lifts a mute.|
| | |Example: ``!unmute <target> [reason]``|
|userinfo|2|Shows information about the chosen user|
| | |Example: ``![userinfo|info] [user]``|


#Reminders
Default permission requirement: public (0)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|remind|0|Base command for reminders|
| | |Example: ``![remind|r|reminder]``|
|remind me|0|Schedule to be reminded about something|
| | |Example: ``!remind [me|add|m|a] <duration> <reminder>``|


#Serveradmin
Default permission requirement: admin (3)

|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|configure|3|Configure server specific settings.|
| | |Example: ``![configure|config|cfg]``|
|configure prefix|3|Sets or show the server prefix|
| | |Example: ``!configure prefix [new_prefix]``|
|configure admin_roles|3|Show or configure server admin roles|
| | |Example: ``!configure [admin_roles|adminroles]``|
|configure admin_roles add|3||
| | |Example: ``!configure admin_roles add <role>``|
|configure admin_roles remove|3||
| | |Example: ``!configure admin_roles remove <role>``|
|configure mod_roles|3|Show or configure server mod roles|
| | |Example: ``!configure [mod_roles|modroles]``|
|configure mod_roles add|3||
| | |Example: ``!configure mod_roles add <role>``|
|configure mod_roles remove|3||
| | |Example: ``!configure mod_roles remove <role>``|
|configure trusted_roles|3|Show or configure server trusted roles|
| | |Example: ``!configure [trusted_roles|trustedroles]``|
|configure trusted_roles add|3||
| | |Example: ``!configure trusted_roles add <role>``|
|configure trusted_roles remove|3||
| | |Example: ``!configure trusted_roles remove <role>``|
|configure mute_role|3|Sets what role to use for muting people.|
| | |Example: ``!configure [mute_role|muterole] <role>``|
|configure self_roles|3|Allows adding/removing roles from the self assignable list|
| | |Example: ``!configure [self_roles|selfrole|self_role]``|
|configure self_roles add|3||
| | |Example: ``!configure self_roles add <role>``|
|configure self_roles remove|3||
| | |Example: ``!configure self_roles remove <role>``|
|configure invite_whitelist|3|Allows adding/removing servers from the invite whitelist, only enforced when there are servers on the list|
| | |Example: ``!configure invite_whitelist``|
|configure invite_whitelist add|3||
| | |Example: ``!configure invite_whitelist add <server>``|
|configure invite_whitelist remove|3||
| | |Example: ``!configure invite_whitelist remove <server>``|
|configure ignored_users|3|Configures users to ignore for edit/delete logs (like bots spamming the logs with edits|
| | |Example: ``!configure [ignored_users|ignoredUsers]``|
|configure ignored_users add|3||
| | |Example: ``!configure ignored_users add <user>``|
|configure ignored_users remove|3||
| | |Example: ``!configure ignored_users remove <user>``|
|configure cog_overrides|3|Configure permission overrides for cogs.|
| | |Example: ``!configure cog_overrides``|
|configure cog_overrides add|3||
| | |Example: ``!configure cog_overrides add <cog> <perm_lvl>``|
|configure cog_overrides remove|3||
| | |Example: ``!configure cog_overrides remove <cog>``|
|configure command_overrides|3|Configure permission overrides for individual commands, this ignores any overrides.|
| | |Example: ``!configure command_overrides``|
|configure command_overrides set|3||
| | |Example: ``!configure command_overrides [set|add] <command> <perm_lvl>``|
|configure command_overrides remove|3||
| | |Example: ``!configure command_overrides remove <command>``|
|configure perm_denied_message|3|Configure if a message should be shown if someone tries to run a command they do not have access to|
| | |Example: ``!configure perm_denied_message <value>``|
|configure language|3|Sets the language to use on this server.|
| | |Example: ``!configure language [lang_code]``|
|configure lvl4|5|Allows adding/removing people to lvl 4 permission lvl for a command.|
| | |Example: ``!configure lvl4``|
|configure lvl4 add|5||
| | |Example: ``!configure lvl4 add <command> <person>``|
|configure lvl4 remove|5||
| | |Example: ``!configure lvl4 remove <command> <person>``|
|configure logging|3||
| | |Example: ``!configure logging``|
|configure logging add|3||
| | |Example: ``!configure logging add <channel> <types>``|
|configure logging remove|3||
| | |Example: ``!configure logging remove <cid> <types>``|
|configure logging dash|3||
| | |Example: ``!configure logging dash``|
|configure features|3||
| | |Example: ``!configure features``|
|configure features enable|3||
| | |Example: ``!configure features enable <types>``|
|configure features disable|3||
| | |Example: ``!configure features disable <types>``|
|configure ignored_channels|3|Configures ignored channels|
| | |Example: ``!configure ignored_channels``|
|configure ignored_channels changes|3|Configures channels to ignore for logging channel changes|
| | |Example: ``!configure ignored_channels changes``|
|configure ignored_channels changes add|3|Adds a channel to the ignored list|
| | |Example: ``!configure ignored_channels changes add <channel>``|
|configure ignored_channels changes remove|3|Removes a channel from the ignored list again|
| | |Example: ``!configure ignored_channels changes remove <channel>``|
|configure ignored_channels changes list|3|Shows the list of channels currently on the ignore list|
| | |Example: ``!configure ignored_channels changes list``|
|configure ignored_channels edits|3|Configures channel to ignore for edit and delete logs|
| | |Example: ``!configure ignored_channels [edits|edit]``|
|configure ignored_channels edits add|3|Adds a channel to the ignored list|
| | |Example: ``!configure ignored_channels edits add <channel>``|
|configure ignored_channels edits remove|3|Removes a channel from the ignored list again|
| | |Example: ``!configure ignored_channels edits remove <channel>``|
|configure ignored_channels edits list|3|Shows the list of channels currently on the ignore list|
| | |Example: ``!configure ignored_channels edits list``|
|configure dm_on_warn|3|Configure warning behaviour for DMs (off by default)|
| | |Example: ``!configure dm_on_warn <value>``|
|configure log_embeds|3||
| | |Example: ``!configure log_embeds <value>``|
|configure blacklist|3||
| | |Example: ``!configure blacklist``|
|configure blacklist add|3||
| | |Example: ``!configure blacklist add <word>``|
|configure blacklist remove|3||
| | |Example: ``!configure blacklist remove <word>``|
|configure role_list|3|Configures or shows the managed roles config list|
| | |Example: ``!configure role_list``|
|configure role_list add|3|Adds a role to the configuration list|
| | |Example: ``!configure role_list add <role>``|
|configure role_list remove|3|Removes a role from the configuration list|
| | |Example: ``!configure role_list [remove|rmv] <role>``|
|configure role_list mode|3|Sets if the list is a whitelist or blacklist|
| | |Example: ``!configure role_list mode <mode>``|
|configure timezone|3||
| | |Example: ``!configure timezone [new_zone]``|
|disable|3|Base command for disabling features|
| | |Example: ``!disable``|
|disable mute|3|Disable the mute feature|
| | |Example: ``!disable mute``|


