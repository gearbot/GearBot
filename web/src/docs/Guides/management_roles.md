# Assigning special roles
**NOTE**: On most servers only the mute role needs to be configured.

## Admin roles
If you have any admin roles, for GearBot this means roles that are lvl 3 and should be allowed to run level 3 commands (configure commands by default), but do not have administrator permission enabled on that role. Then you need to mark those roles as admin roles.

To add a role to the admin role list:
```
!configure admin_roles add <role>
```
Where ``<role>`` is either the full role name (case sensitive), the role id, or a role mention (not recommended unless you want to summon all your admins at once)

And if you later want to remove the role from the list again:
```
!configure admin_roles remove <role>
```

## Moderator roles
Very similar, but for level 2 commands: moderation commands.

If you need to add any roles to this list you might want to rethink your server permissions. While this bot is very reliable and i do my best to achieve 24/7 uptime, small interruptions are always possible for different reasons (discord outage disconnecting bots?). If your mods do not have ban member permissions during this time, things might end badly if a troll decides to stop by.

Regardless, the commands are very similar:
```
!configure mod_roles add <role>
```
and
```
!configure mod_roles remove <role>
```

## Trusted roles
This is nothing GearBot can detect, and not always needed, this is mostly so you can have fun commands that some people like to abuse and use a little too much (cat, dog, coinflip, ...) not public but gated behind a role for only some users.

Same deal here:
```
!configure trusted_roles add <role>
```
and
```
!configure trusted_roles remove <role>
```

## Muted role
And then to finish it up: a role that is and works completely different!

The mute role is added to people to mute them. When you configure the role it adds an permission override on all channels denying it send messages and add reaction permissions. This is also done for new channels created later. 

If someone tries to dodge the mute while one is active (through the bot, manually applying the role won't work for this) the role is just re-added upon joining
```
!configure mute_role <role>
```