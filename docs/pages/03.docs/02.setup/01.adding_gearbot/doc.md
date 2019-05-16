---
title: Adding GearBot
---
# Adding the bot
The first step is to add GearBot to the server and prepare a few things so he can work. If you click on the following link you can add him with the permissions he needs. Below is an explanation of why he needs what permissions if you don't want him to have all these permissions.
[Click here to add GearBot](https://discordapp.com/oauth2/authorize?client_id=349977940198555660&scope=bot&permissions=1342565590).

# Permissions
- Manage roles
    - This allows him to add/remove roles from people, this is used for selfroles, muting and the mod role command to add/remove roles from people 
- Manage channels
    - Needed to create the channel overrides that makes the mute role work, both on current channels and new channels
- Kick members
    - Kick people with the kick command
- Ban members
    - Ban people with the ban command
- View audit log
    - Allows accessing the audit log to convert manual kicks/bans to infractions, as well as enhancing a lot of logging to show who did the action
- Read messages/Send messages/Embed links/Attach files/Read message history/Add reactions/Use external emoji
    - Just basic permissions to interact with chat, not all servers give these permissions to the everyone role
- Manage messages
    - Allows removing messages with the clean commands and cleaning command trigger messages in some cases
  
# Positioning the role
Next up is repositioning the GearBot role that got created when the bot entered the server. You want to move this role (or another role if you give it an additional bots role) to be above all the roles you want him able to add/remove from people (mute role for example) and who's members you want to be able to kick with the bot (if you have cosmetic roles, like a member role, and that is above GearBot's highest role he won't be able to kick/ban them).
