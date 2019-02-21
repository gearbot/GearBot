import re

ID_MATCHER = re.compile("<@!?([0-9]+)>")
ROLE_ID_MATCHER = re.compile("<@&([0-9]+)>")
CHANNEL_ID_MATCHER = re.compile("<#([0-9]+)>")
URL_MATCHER = re.compile(r'((?:https?://)[a-z0-9]+(?:[-.][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n<>]*)?)', re.IGNORECASE)
EMOJI_MATCHER = re.compile('<(a?):([^: \n]+):([0-9]+)>')
JUMP_LINK_MATCHER = re.compile(r"https://(?:canary|ptb)?\.?discordapp.com/channels/\d*/(\d*)/(\d*)")
MODIFIER_MATCHER = re.compile(r"^\[(.*):(.*)\]$")
NUMBER_MATCHER = re.compile(r"\d+")
START_WITH_NUMBER_MATCHER = re.compile(r"^(\d+)")
INVITE_MATCHER = re.compile(r"(?:https?://)?(?:www\.)?(?:d\s*i\s*s\s*c\s*o\s*r\s*d\s*(?:\.| |\[\s*d\s*o\s*t\]|\s)*(?:\s*g\s*g\s*|\s*i\s*o\s*|\s*m\s*e\s*|\s*l\s*i\s*)|\s*d\s*i\s*s\s*c\s*o\s*r\s*d\s*a\s*p\s*p\s*\.\s*c\s*o\s*m\s*/\s*i\s*n\s*v\s*i\s*t\s*e\s*)+/\s*((?:(?!https?)[\w\d-])+)", flags=re.IGNORECASE)