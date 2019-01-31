from tornado.web import removeslash

from Other import BackendUtils
from Other.PrimaryHandler import PrimaryHandler


class AuthSetTestingEndpoint(PrimaryHandler):
    @removeslash
    async def get(self):
        self.set_secure_cookie(
            name = "userauthtoken",
            value = BackendUtils.TESTING_USERID
        )
        self.write("Auth cookie set!")