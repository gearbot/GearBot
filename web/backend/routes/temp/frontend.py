from tornado import escape
from tornado.web import authenticated, removeslash

from Other import BackendUtils
from Other.PrimaryHandler import PrimaryHandler


class FrontendAPIGuildInfo(PrimaryHandler):
    @authenticated
    @removeslash
    async def post(self):
        userID = self.get_current_user()
        guild_perms_data = await BackendUtils.get_guilds_info(userID)
        self.write(escape.json_encode(guild_perms_data))
        self.finish()