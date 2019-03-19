#Basic
|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|dog|0|Random dogs!|
|self_role|0|Shows self-assignable roles or assigns/removes one.|
|ping|0|See if the bot is still online.|
|cat|0|Random cats!|
|help|0|Lists all commands, the commands from a cog or info about a command.|
|jumbo|0|Jumbo emoji|
|quote|0|Quotes the requested message.|
|about|0|Shows some runtime info like uptime, messages seen and link to support server.|
|coinflip|0|Random decision making.|


#Moderation
|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|mban|2|Bans multiple users with the same reason|
|purge|2|Purges up to 1000 messages in this channel.|
|userinfo|2|Shows information about the chosen user|
|softban|2|Soft bans a user from the server (ban, removes last day of messages and unbans).|
|seen|2||
|unban|2|Unbans a user from the server.|
|ban|2|Bans a user from the server.|
|kick|2|Kicks a user from the server.|
|role|2|mod_role_help|
|role add|2|Adds a role to someone|
|role remove|2|Removes a role from someone|
|role remove|2|Removes a role from someone|
|clean|2|Gets out the broom to clean whatever mess needs cleaning|
|clean user|2|Removes messages by a specific user|
|clean bots|2|Removes messages send by any bot|
|clean all|2|Just clean everything|
|clean last|2|Cleans all messages send in the last x time (5 m for example)|
|clean until|2|Cleans until the given message (message is also removed)|
|clean between|2|Cleans both messages given and everything in between|
|mute|2|Temporarily mutes someone.|
|forceban|2|Bans a user even if they are not in the server.|
|roles|2|Prints a list of all roles in the server, possible modes are alphabetic or hierarchy (default)|
|serverinfo|2|Shows information about the current server.|
|tempban|2|Bans a user from the server.|
|mkick|2|mkick help|
|archive|2|Base command for archiving, use the subcommands to actually make archives|
|archive channel|2|Archive messages from a channel|
|archive user|2|Archive messages from a user|
|unmute|2|Lifts a mute.|


#Serveradmin
|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|disable|3|Base command for disabling features|
|disable mute|3|Disable the mute feature|
|configure|3|Configure server specific settings.|
|configure prefix|3|Sets or show the server prefix|
|configure admin_roles|3|Show or configure server admin roles|
|configure admin_roles add|3||
|configure admin_roles remove|3||
|configure admin_roles|3|Show or configure server admin roles|
|configure admin_roles add|3||
|configure admin_roles remove|3||
|configure mod_roles|3|Show or configure server mod roles|
|configure mod_roles add|3||
|configure mod_roles remove|3||
|configure mod_roles|3|Show or configure server mod roles|
|configure mod_roles add|3||
|configure mod_roles remove|3||
|configure trusted_roles|3|Show or configure server trusted roles|
|configure trusted_roles add|3||
|configure trusted_roles remove|3||
|configure trusted_roles|3|Show or configure server trusted roles|
|configure trusted_roles add|3||
|configure trusted_roles remove|3||
|configure mute_role|3|Sets what role to use for muting people.|
|configure mute_role|3|Sets what role to use for muting people.|
|configure self_roles|3|Allows adding/removing roles from the self assignable list|
|configure self_roles add|3||
|configure self_roles remove|3||
|configure self_roles|3|Allows adding/removing roles from the self assignable list|
|configure self_roles add|3||
|configure self_roles remove|3||
|configure invite_whitelist|3|Allows adding/removing servers from the invite whitelist, only enforced when there are servers on the list|
|configure invite_whitelist add|3||
|configure invite_whitelist remove|3||
|configure ignored_users|3|Configures users to ignore for edit/delete logs (like bots spamming the logs with edits|
|configure ignored_users add|3||
|configure ignored_users remove|3||
|configure ignored_users|3|Configures users to ignore for edit/delete logs (like bots spamming the logs with edits|
|configure ignored_users add|3||
|configure ignored_users remove|3||
|configure cog_overrides|3|Configure permission overrides for cogs..|
|configure cog_overrides add|3||
|configure cog_overrides remove|3||
|configure command_overrides|3|Configure permission overrides for individual commands, this ignores any overrides.|
|configure command_overrides set|3||
|configure command_overrides set|3||
|configure command_overrides remove|3||
|configure perm_denied_message|3|perm_denied_message_help|
|configure language|3|Sets the language to use on this server.|
|configure lvl4|3|Allows adding/removing people to lvl 4 permission lvl for a command.|
|configure lvl4 add|3||
|configure lvl4 remove|3||
|configure logging|3||
|configure logging add|3||
|configure logging remove|3||
|configure logging dash|3||
|configure features|3||
|configure features enable|3||
|configure features disable|3||
|configure dm_on_warn|3|Configure warning behaviour for DMs (off by default)|
|configure log_embeds|3||
|configure blacklist|3||
|configure blacklist add|3||
|configure blacklist remove|3||
|configure role_list|3|Configures or shows the managed roles config list|
|configure role_list add|3|Adds a role to the configuration list|
|configure role_list remove|3|Removes a role from the configuration list|
|configure role_list remove|3|Removes a role from the configuration list|
|configure role_list mode|3|Sets if the list is a whitelist or blacklist|


#CustCommands
|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|commands|0|Lists all custom commands for this server, also the base command to making, updating and removing them.|
|commands create|2|Create a new command|
|commands create|2|Create a new command|
|commands create|2|Create a new command|
|commands remove|2|Removes a custom command|
|commands update|2|Sets a new reply for the specified command|


#Infractions
|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|inf|2|Base infractions command, see the sub-commands for details.|
|inf search|2|Shows all infractions given by or to a given user.|
|inf update|2|Updates an infraction.|
|inf delete|5|Deletes an infraction. This can not be undone!|
|inf delete|5|Deletes an infraction. This can not be undone!|
|inf delete|5|Deletes an infraction. This can not be undone!|
|warn|2|Adds a new warning, the user is not informed of this.|


#Minecraft
|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|cf|0|Base command to pull mod info from curseforge, still WIP|
|cf info|0||


#Reminders
|   Command | Default lvl | Explanation |
| ----------------|--------|-------------------------------------------------------|
|remind|0|Base command for reminders|
|remind me|0|Schedule to be reminded about something|
|remind me|0|Schedule to be reminded about something|
|remind me|0|Schedule to be reminded about something|
|remind me|0|Schedule to be reminded about something|


