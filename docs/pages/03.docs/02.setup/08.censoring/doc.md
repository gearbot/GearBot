---
title: Censoring
---
# Censoring

GearBot currently supports 2 types of censoring:

- invite censoring
- text censoring

But none of these apply to people who have permission level 2 or higher (mods and admins), level 4 does not count as this only applies to specific commands, not globally.
## Initial setup
First you need to make sure there is a logging channel that has the ``CENSOR_MESSAGES`` key so that censor actions are logged there, this is a requirement to being able to enable censoring of messages.

Next up is making sure the feature is enabled, you can do this by running:
```
!configure features enable CENSOR_MESSAGES
```

## Setting up invite censoring
Invite censoring does not kick in until there are servers on the whitelist. If you do not want any external invites to be posted you can just add your server to the whitelist and no others.

**Note:** All these commmands uses server IDs and do not validate if these are actual, valid server IDs. This is due to that the bot cannot request a server from the API with its ID if the bot is not on that server.

To add a server to the whitelist:
```
!configure allowed_invites add <serverid>
```
Similar story to remove one:
```
!configure allowed_invites remove <serverid>
```
And to view the entire list:
```
!configure allowed_invites
```

## Setting up text censoring
Text censoring works with partial text matches and is case insensitive.

**WARNING:** Be very careful for partial matches as this does not differentiate if it's in the middle of a word or a word on it's own.

To add something to the censor_list:
```
!configure censor_list add <thing>
```
To remove:
```
!configure censor_list remove <thing>
```
