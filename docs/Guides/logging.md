#**Advanced logging**
So you want to do more then just log everything in a single channel? Then this guide is for you. 

GearBot can log the following things (these are also the keys you use in the configure commands):
 - EDIT_LOGS
 - NAME_CHANGES
 - ROLE_CHANGES
 - CENSORED_MESSAGES
 - JOIN_LOGS
 - MOD_ACTIONS
 - COMMAND_EXECUTED
 - FUTURE_LOGS
 
FUTURE_LOGS is a special one, this one doesnt log anything, it is merely a placeholder. When new logging types are added, having this one configured means they will automatically be added and enabled.
Another special case is "EVERYONE", this isn't a key on it's own, but when running a command this will get replaced by the full list of available keys. So if you want all of them you do not have to type them one by one (also means that if you want all but one type, you can add everything, and then just remove the on you don't want).
All keys are case insensitive so you can type them in upper or lower case when using in the commands.

These commands are also made to be user friendly and help you in figuring out why things do not work. As such things can be a bit verbose and when you try to enable/disable things that are already enabled/disabled it will inform you. It will also let you know if you specified any invalid logging keys (but still process the valid ones)

##**Adding logging to channels**
To add logging to a channel you can simply use the following command
```
!configure logging add <channel> <types>
```
Types can be a single type, everything, or a list of types.

###*Some examples*
```
!configure logging add #mod-logs everything
```

```
!configure logging add #mod-logs EDIT_LOGS, NAME_CHANGES, ROLE_CHANGES
```

##**Verifying logging status**
If for some reason you are unsure of what exactly is configured to be logged or not you can use the following commands to help you figure out what is going on.
```
!configure logging
```
This will show you all the currently configured channels, if all required permissions to log are set correctly and what will be logged.

```
!configure features
```
Shows the enabled features, for most logging there is no special feature that needs to be enabled, but things like edit and censor logs are linked to features.


##**Removing logging from a channel**
If you no longer want some keys to be logged to the channel you can remove them again:
```
!configure logging remove <channel> <keys>
```
