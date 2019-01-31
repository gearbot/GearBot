from tornado.web import RequestHandler
import json

config = json.load(open("config/web.json"))
CORS_ORGINS = config["CORS_ORGINS"]

class PrimaryHandler(RequestHandler):
    def get_current_user(self):
        userIDCookie = self.get_secure_cookie("userauthtoken")
        if userIDCookie is not None:
            return userIDCookie.decode()
        else:
            return None

    def set_default_headers(self):
        for cor_orgin in CORS_ORGINS:
            self.set_header("Access-Control-Allow-Origin", cor_orgin)
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header("Access-Control-Allow-Credentials", "true")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')