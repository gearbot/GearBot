from tornado.web import RequestHandler
import json

import socketio
from socketio import AsyncNamespace

# WebSocket Namespaces
from routes.api.guids import Guilds

sio = socketio.AsyncServer(async_mode="tornado")
_Handler = socketio.get_tornado_handler(sio)

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

class SocketHandler(_Handler):
    def check_origin(self, origin):
        if origin in CORS_ORGINS:
            return True
        else:
            return False

class APIMain(AsyncNamespace):
    async def on_connect(self, sid, environ):
        print("A socket connected!")
        await self.emit("api_response",
            data = "Hello Dashboard!"
        )


    

sio.register_namespace(APIMain("/api/"))
sio.register_namespace(Guilds("/api/guilds"))