#**What is archiving?**
Archiving gives you the ability to collect messages by a specific user or in a channel and keep them in a text file format. By default this is available to moderators and above (permissions lvl 2 and higher). 
#**How can I archive?**
First of all with archiving there are two options, you can either archive messages sent by a user or messages sent in a channel.
When you run the command, the bot sends a text file with all the messages that you specified to archive. The file includes all information such as timestamps, ids, usernames, content of the messages. This also means the bot needs file upload perms in the channel you use it in (and if you don't want the result archive to be public, don't use it in a public channel) 

#**Arguments that can be passed in:**
<user> - A user's messages to archive (can be a mention or an id)
<channel> - A channel's messages to archive (can be a mention or an id)
<amount> - The amount of messages to archive (up to 5000)

How to use the command for channels:
```!archive channel <channel> <amount>```
When archiving a user's messages:
```!archive user <user> <amount>```
In both cases the amount is optional (defaults to 100 when omitted), for archiving a channel you can also omit the channel and it will default to doing 100 messages in the current channel
#**Examples:**
Archiving a user's messages:
```!archive user @AEnterprise#4693 ```
Archiving a channel's messages:
```!archive channel #test-channel 5000```
