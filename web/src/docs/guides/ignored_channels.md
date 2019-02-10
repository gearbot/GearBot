# Ignored channels

These features are only intended to be used if you have music bots or so that are spamming your logs with constant channel topic changes. For bots with constant edits please consider adding them as ignored user instead, as this will disable logging and can thus be abused by others to hide what they are doing.

## Ignoring channel changes
Some music bots edit a channel topic to match what they are playing. While this is neat, this results in a lot of spam in the modlogs. And if you still want changes logged about other channels, disabling it is a bit tricky. Instead GearBot can just ignore the changes to that particular (set of) channel(s).

To see all channels currently being ignored for change logs:
```
!configure ignored_channels changes list
```

Adding a channel can be done with:
```
!configure ignored_channels changes add <channel>
```

Removing it from the list again is very similar:
```
!configure ignored_channels changes remove <channel>
```

# Ignoring channel edit logs
Be VERY careful with ignoring edits from channels completely, anyone can send nasty messages and then edit or remove them after, with no trace in the logs.
But the commands are very similar:
```
!configure ignored_channels edits list
!configure ignored_channels edits add <channel>
!configure ignored_channels edits remove <channel>
```
