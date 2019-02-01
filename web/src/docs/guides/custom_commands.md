# What are custom commands?
Custom commands are very basic commands you can make yourself (provided you have permission lvl 2 or higher for these commands). You give gearbot a trigger and a reply. When someone does `!<trigger>`, gearbot will reply with the reply you gave him.
# How do I create custom commands?
You can create a custom command using the `!commands create` command. You may also use `!commands new` or `!commands add`, which are variations of this command that do the same function.
You will need to provide both a trigger and a reply to create custom commands.
```
!commands create <trigger> <reply>
```
Please mind the trigger can not have spaces in it.

Once done this, you may use the command by saying
```
!<trigger>
```
To change the reply of a command, use this command.
```
!commands update <trigger> <reply>
```
However, using `!commands create/add/new` instead of `!commands update`will work (requires confirmation), same as using `!commands update` instead of `!commands create/add/new`.

To remove a command, use
```
!commands remove <trigger>
```
# Who can use custom commands?
Everyone can use them, everyone can also request the list of all custom commands by just executing ``!commands``.
