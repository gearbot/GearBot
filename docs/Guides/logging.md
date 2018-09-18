#**Advanced logging**
So you want to do more then just log everything in a single channel? Then this guide is for you.

Keep in mind there are 2 main steps required to make logging happen:
1) Configure one or more channels to receive logs
2) Tell what keys should be logged to what channels
3) Enable the logging of the key on a server lvl. This allows GearBot to be pre-configured as backup bot, or disable no longer wanted logging that is being send to multiple channels globally.

To assist in this GearBot will help by executing commands for you if you want. If you try to add logging to a channel that is not setup for logging yet, it will set it up for you (after asking for confirmation). Similarly if you configure a logging key to be logged to a channel but have not enabled it on a server lvl it will offer to enable it for you. 

GearBot can log the following things (these are also the keys you use in the configure commands):
 - EDIT_LOGS
 - NAME_CHANGES
 - ROLE_CHANGES
 - CENSOR_LOGS
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
!configure log_channels add_logging <channel> <types>
```
Types can be a single type, everything, or a list of types.

###*Some examples*
```
!configure log_channels add_logging #mod-logs everything
```

```
!configure log_channels add_logging #mod-logs EDIT_LOGS, NAME_CHANGES, ROLE_CHANGES
```

##**Verifying logging status**
If for some reason you are unsure of what exactly is configured to be logged or not you can use the following commands to help you figure out what is going on.
```
!configure log_channels
```
This will show you all the currently configured channels, if all required permissions to log are set correctly, what will be logged, and what is configured to be logged but disabled on the server.

```
!configure log_types
```
Is similar but only shows what logging types are enabled/disabled on the server. Also a useful command if you want get the list of all keys.

##**Enabling logging for the key**
You also need to enable this for things to actually be logged, GearBot will offer to do this for you if you configure the key, but if you accidentally declined it, or didn't want it on yet and want to enable it afterwards:
```
!configure log_types enable 
```

##**Removing logging from a channel**
If you no longer want some keys to be logged to the channel you can remove them again:
```
!configure log_channels remove_logging <channel> <keys>
```


##**Removing the channel as logging channel**
When you no longer want any logging you can remove the channel from the log channels list completely:
```
!configure log_channels remove <channel>
```
GearBot will ask for confirmation if there still are things configured to be logged there
