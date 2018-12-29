#Introduction to permissions
At it's core GearBot uses a very basic permissions system that determines who is able to run what commands.

```
╔════╦═════════════════╦═══════════════════════════════════════════════════╗
║ Nr ║      Name       ║                    Requirement                    ║
╠════╬═════════════════╬═══════════════════════════════════════════════════╣
║  0 ║ Public          ║ Everyone                                          ║
║  1 ║ Trusted         ║ People with a trusted role or mod+                ║
║  2 ║ Mod             ║ People with ban permissions or admin+             ║
║  3 ║ Admin           ║ People with administrator perms or an admin role  ║
║  4 ║ Specific people ║ People you added to the whitelist for a command   ║
║  5 ║ Server owner    ║ The person who owns the server                    ║
║  6 ║ Disabled        ║ Perm level nobody can get, used to disable stuff  ║
╚════╩═════════════════╩═══════════════════════════════════════════════════╝
```
**NOTE**: Bot owner commands to manage and update the bot fall outside of this permissions system and are handled separately, similarly bot ownership is not part of these permissions checks and has no effect on that. 

For example: all commands in the basic cog have a default permission requirement of 0, allowing anyone to run them. This can be changed with an override (see the next section for more details) to only allow mods, or even nobody to run these commands.

And similarly you can also lower the requirement for some commands (up to a point), commands like userinfo are by default mod only but can be made public.

See [the command list](../commands.md) for a the default permission requirement per command.