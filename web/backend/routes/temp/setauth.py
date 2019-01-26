from tornado.web import removeslash

from web.backend.Other import BackendUtils
from web.backend.Other.PrimaryHandler import PrimaryHandler


class AuthSetTestingEndpoint(PrimaryHandler):
    @removeslash
    async def get(self):
        self.set_secure_cookie(
            name = "userauthtoken",
            value = BackendUtils.TESTING_USERID
        )
        self.write("Auth cookie set!")