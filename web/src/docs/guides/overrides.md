# Reconfiguring command requirements
**Note:** While this is possible it is not required to do so on all servers, if the defaults work for you, there is no need to add any overrides.

To determine the permission level required to run a command it looks in the following order, and uses the first one it finds:
1) a command override for that specific command
2) a command override for the parent command (recursive) if this is a subcommand (so if you add an override to the `` role`` command, but not to the ``role add`` subcommand, the top first will apply)
3) a cog override for the cog this command belongs to
4) default permission requirement for the command (most do not have one, only a few have this)
5) default permission requirement for the cog this command belongs to


## About cogs
Commands are grouped into cogs, groups of commands if you will. If you look at the [command list](../commands), the commands are listed there, together with their default command level.

# Cog overrides
If you want to add a cog override:
```
!configure cog_overrides add <cog> <level>
```
**Note:** Cog names are case sensitive!

To remove it later:
```
!configure cog_overrides remove <cog> <level>
```

You can also get a list of all configured cog overrides:
```
!configure cog_overrides
```

# Command overrides
If cog overrides are to big for what you want to adjust, you can also adjust it for individual commands (or subcommands if you wrap it in quotation marks):
```
!configure command_overrides add <command> <level>
```
You can also remove them again:
```
!configure command_overrides remove <command> <level>
```
And view the list of what you have configured:
```
!configure command_overrides
```
