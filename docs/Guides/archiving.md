**What is archiving?**
Archiving gives you the ability to collect messages by a specific user or in a channel and keep them in a text file format. The command's permission level is Moderator (Level 2 in the permissions table).
**How can I archive?**
First of all with archiving there are two options, you can either archive messages sent by a user or messages sent in a channel. When you run the command, the bot sends a text file with all the messages that you specified to archive. The file includes all information such as timestamps, ids, usernames, content of the messages.

**Arguments that need to be passed in:**
<user> - A user's messages to archive (can be a mention or an id)
<channel> - A channel's messages to archive (can be a mention or an id)
<amount> - The amount of messages to archive

How to use the command:
```!archive <user>|<channel> <amount>```
When archiving a user's messages:
```!archive <user> <amount>```
When archiving a channel's messages:
```!archive <channel> <amount>```
**Examples:**
Archiving a user's messages:
```!archive @AEnterprise#4693 100```
Archiving a channel's messages:
```!archive #test-channel 100```
