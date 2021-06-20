import re

ID_MATCHER = re.compile("<@!?([0-9]{15,20})>")
ROLE_ID_MATCHER = re.compile("<@&([0-9]{15,20})>")
CHANNEL_ID_MATCHER = re.compile("<#([0-9]{15,20})>")
MENTION_MATCHER = re.compile("<@[!&]?\\d+>")
URL_MATCHER = re.compile(r'((?:https?://)[a-z0-9]+(?:[-._][a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?(?:/[^ \n<>]*)?)', re.IGNORECASE)
EMOJI_MATCHER = re.compile('<(a?):([^: \n]+):([0-9]{15,20})>')
JUMP_LINK_MATCHER = re.compile(r"https://(?:canary|ptb)?\.?discord(?:app)?.com/channels/\d{15,20}/(\d{15,20})/(\d{15,20})")
MODIFIER_MATCHER = re.compile(r"^\[(.*):(.*)\]$")
NUMBER_MATCHER = re.compile(r"\d+")
ID_NUMBER_MATCHER = re.compile(r"\d{15,19}")
START_WITH_NUMBER_MATCHER = re.compile(r"^(\d+)")
INVITE_MATCHER = re.compile(r"(?:https?://)?(?:www\.)?(?:discord(?:\.| |\[?\(?\"?'?dot'?\"?\)?\]?)?(?:gg|io|me|li)|discord(?:app)?\.com/invite)/+((?:(?!https?)[\w\d-])+)", flags=re.IGNORECASE)