#**Permissions**
Permissions is useful to control who can tell GearBot to do certain things and use certain commands, or maybe you want to disable a function of GearBot completely. So lets go over the permissions levels and get started with permission managing.

#**Different permission levels**
GearBot have different permission levels and are classified like this:
```
╔════╦═════════════════╦═══════════════════════════════════════════════════╗
║ Nr ║      Name       ║                    Requirement                    ║
╠════╬═════════════════╬═══════════════════════════════════════════════════╣
║  0 ║ Public          ║ Everyone                                          ║
║  1 ║ Trusted         ║ People with a trusted role or mod+                ║
║  2 ║ Mod             ║ People with ban permissions or admin+             ║
║  3 ║ Admin           ║ People with administrator perms or an admin role  ║
║  4 ║ Specific people ║ People you added to the whitelist                 ║
║  5 ║ Server owner    ║ The person who owns the server                    ║
║  6 ║ Disabled        ║ Perm level nobody can get, used to disable stuff  ║
╚════╩═════════════════╩═══════════════════════════════════════════════════╝
```
If a command or Cog has a certain permission level it means that the user needs to have the requirement for that level in order to use it.

#**Change the permissions for a Cog**
(Note: You don't need to assign permission levels, Gearbot already has preconfigured values that will work for most servers. But incase you feel like modifying the standard permissions, Proceed!)
Inorder to use these commands you'll need permission level 3 or higher.
In this section we will get started with changing/overriding the standard permission levels used by GearBot.

You're able to use this command to modify the required permission level of any Cog.
```
!configure cog_overrides add <cog> <Permission-Level>
```

If you've made a mistake or just want to go back to the previous level for a certain Cog, all you need to do is use this command.
```
!configure cog_overrides remove <cog>
```
