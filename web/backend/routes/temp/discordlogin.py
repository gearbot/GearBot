from tornado.web import removeslash

from web.backend.Other import BackendUtils
from web.backend.Other.PrimaryHandler import PrimaryHandler


class DiscordOAuthRedir(PrimaryHandler):
    @removeslash
    async def get(self):
        self.redirect(
            permanent = False,
            url = f"{BackendUtils.API_LOCATION}/oauth2/authorize?client_id={BackendUtils.CLIENT_ID}&redirect_uri={BackendUtils.REDIRECT_URI}&response_type=code&scope=identify%20guilds"
        )