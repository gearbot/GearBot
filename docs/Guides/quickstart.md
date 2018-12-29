![Quickstart header](../img/quickstart.png)
#**Inviting**
First you want to do is add GearBot to your server. Unlike regular users a normal invite link can't be used by bots but you can add GearBot  to your server by following this link: <https://discordapp.com/oauth2/authorize?client_id=349977940198555660&scope=bot&permissions=268823766>.
There you will be able to pick what server you want to add GearBot to as well it will list the permission GearBot will be granted (as he'll need those for different things to work).


If GearBot has been on the server before it will continue on where it left of before and he will re-use the configurations he already has.

To run any configuration commands you need permission lvl 3 (admin) or higher, see the advanced guide for details, for now it's enough to know that by default you have this if you are the server owner or have a role with the"administrator" permission enabled. If all people who you want to be able to reconfigure GearBot have admin perms, and all moderators have ban permissions: Congrats you are done for this bit and can skip ahead!



If for some reason this is not the case you will have to tell GearBot what the admin and mod roles are. Please replace ``<role>`` with the actual role name (case sensitive) or ID (can be gotten with the ``!roles`` command)

To add a role as mod role:
```
!configure mod_roles add <role>
```

If you no longer want a role to be considered a modrole (keep in mind this is seperate from roles with ban permissions, those people will GearBot always consider to be mods):
```
!configure mod_roles remove <role>
```

For admin roles the process is similar:
```
!configure admin_roles add <role>
```
and
```
!configure admin_roles remove <role>
```


#**Logging**

GearBot has different types of modlogs, with more being planned.
Setting it up is also really easy if you just want a single channel where everything is logged in, for more complex setups see [Advanced Logging](logging.md)

The command to kick it all off:
```
!configure logging add #test-logging everything
```
This will log everything to the channel and ask you to enable the edit and censor features, if you want to use these, just react with the yes emoji. Censoring won't actually do anything until you configure blacklisted words or add servers to the invite whitelist.
