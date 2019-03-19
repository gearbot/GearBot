# Raid shields
GearBot can help guard against raids, preventing them is (sadly) impossible, but a lot can be done to mitigate them! But not every detection and action solution works for all server.
Bring in the shields:

Each shield consists of 5 components:
1) trigger
2) termination condition
3) actions to take once triggered
4) actions to take per raider
5) actions to take once the shield goes down again

A server can have multiple shields, as soon as a single one is triggered, the server is considered under raid. Any additional shields that trigger after the initial shield join the same raid and will act on all raiders already in the raid (even if they didn't trigger this shield because different detection timings).
Each shield can only trigger once per raid (to prevent silly things where a shield goes down and then is instantly triggered again and bans everyone twice)

## Triggers
A shield trigger is pretty basic: if x people join in y seconds, it is triggered.


## Termination conditions
There are 3 options for a shield to be terminated
1) after a fixed time
2) after x seconds of nobody new joining
3) being terminated by another shield (see trigger actions)

each shield needs 1 termination condition, being terminated by another is not enough as not all shields might trigger each time

## Trigger actions
These actions are taken when a shield is triggered, only once per raid
options are
- sending a message to a specific channel
- DMing someone a message
- disable another shield (this one is mostly intended to avoid pointless work, if one shield only mutes people, but another bans them, use this to disable the muting shield so raiders just get banned instantly once this shield goes up)

## Actions to take per raider
Once a shield goes up, these actions are taken on all raiders already detected in the raid, as well as any others who join while this shield is up.
Options:
- dm them a message (only recommended for a muting shield with a high risk of false positives)
- mute (needs a duration)
- kick
- ban

## Actions to take upon termination
When the shield goes down again you can take another set of actions, options here are limited, more meant for informing people the raid is over
Options:
- sending a message to a specific channel
- DMing someone a message

# Feedback
All of this is WIP, if you have suggestions for additional actions or improvements, please get in touch