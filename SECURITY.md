# GearBot (And Services) Security Policy

## About

GearBot helps out a large number of Discord guilds, ranging from small and personal to large and heavily moderated. He is primarily designed to make server moderation easier on server staff, but this means that he usually has higher permissions and abilities that could cause nasty repercussions if misused or exploited. These issues could come from a third-party library issue, bad validation, or just a simple mistake inside the code. With the web dashboard and its associated API being brought to life, its more important then ever to ensure that any possible security bugs are caught fast and resolved even quicker.

## Reporting Policy

While transparency is always a good thing, when another user's data is potentially at risk its usually better to keep things private until the issue has been fixed and the risk eliminated. For this reason, we ask that you do **not** publically detail any security vulnerabilities to anyone except the GearBot core team until the issue has been confirmed to be fixed and deployed.

- We go by a 30 day disclosure policy. Once that timeframe is up and if for some reason the bug has not been fixed, the reporter holds all rights to disclose the bug publicly with no restrictions.

- Issues can, and will, be disclosed sooner if they are fixed before then and there is confirmation that no risk remains to any user from the bug. Please keep in mind that it might include some time where we inform people who are running their own instance of the bot and choose to receive notifications will be informed first so they can quietly patch their instances before any information is made public.

- The reporter holds all rights to the bug they find, no NDAs or other blanket covering will ever occur. All that is required is to wait the required 30 days (unless the team gives you permission to disclose sooner).

- Please ensure that any testing and reports are made based off the latest version of the code. Updates are frequent, so ensure that you are on the latest commit.

- Testing should only occur with approval of whoever runs the instance you are testing against.

- Testing should occur in a way that does not impact or minimizes impact on other users of the same instance. This means no trying to get data of specific guilds without their consent. Use your own server and accounts (or make some) wherever possible. If an issue exposes data of random users without control of it, then that is a different matter altogether. However, targeted attacks without consent should not be attempted. Similarly do not attempt any exploits that might result in downtime or other disruptions in the target instance's ability to continue normal operations without explicit permission from whoever runs the instance.

- This is a open source project not backed by any company or organization. As such we do not have the funds to provide any sort of monetary compensation. We do have virtual hugs and gratitude (plus our shiny wall of fame, if you're into that thing)

- Any issue found with libraries GearBot uses that are not maintained by this team does not fall under this policy but the policy of said library, but we would appreciate a heads up if at all possible.

- If you have *any* questions, concerns, or comments about the policy, including if doing something is OK, feel free to reach out for help.

  

## How to report

- Contact AEnterprise#4693 (userid 106354106196570112) or BlackHoleFox#1527 (userid 105076359188979712) on Discord. You can find us on the [GearBot Discord Server](https://discordapp.com/invite/vddW3D9).
- Alternatively you can report via email at: gearbot@gearbot.rocks
- You will receive a reply confirming we received your report within 48h. If you do not get such confirmation it means the person you tried to contact is unavailable for some reason. Please try one of the other methods instead to make sure we receive your report.

## Rules:

1. Adhere strictly to the reporting policy outlined above
2. No brute forcing is permitted. It is unneeded, even for fuzzing. All the code is open source so you can run your own local instance instead for these tasks.
3. No automated scanning tools are permitted for testing.
4. If you encounter another user's data or server, do not interact with it or attempt any modifications. Stop and report the issue immediately!
5. No testing issues on a instance of GearBot you don't own without proper permission. Get permission first or run your own instance.
6. If you are caught violating any of the above rules, you will be banned from the program for the indefinite future and access to GearBot (the public instance) can be revoked.

## Scope and Impact

### Out of scope

- Phishing of any variety
- Denial of Service attacks or DDoS attacks
- Issues on instances *not* hosted by the core team caused by misconfiguration or modifications.

### Testing on the public instance

**Note**: Due to the open source nature of the services, it is always preferable to clone the service locally from the latest master branch for most testing.

The following domains are in scope and can be tested against (provided the rules outlined above are followed, as well as any other additional restrictions outlined below):

- gearbot.rocks

- dash.gearbot.rocks (Do not test any endpoint under /api/admin without explicit permission)

- animal.gearbot.rocks

  **WARNING**: Anything found outside of these areas and domains is considered out-of-scope and does not fall under the program's safe harbor. There might be instances found under other subdomains but these are usually dev versions with WIP stuff that isn't public or meant to be secured yet (or even online much)

### High impact areas

These are the types of issues that have the highest impact and we consider having the highest risks

- ### GearBot Discord Bot:

  - Escalation of privileges, running commands that your user shouldn't be able to normally.

- ### The Dashboard API and its associated frontend:

  - Escalation of privileges, performing actions you shouldn't be authorized for
  - Gaining access as another user, getting their oauth token, etc...
  - Any way to access another user's data

- ### GearBot's public facing animal fact API

  - The admin REST interface for modifying the fact lists
