from tornado.web import RequestHandler
import aioredis
import json
from secrets import token_bytes, token_urlsafe, base64
import hmac
from hashlib import blake2b
from time import time
import asyncio

import socketio
from socketio import AsyncNamespace

sio = socketio.AsyncServer(async_mode="tornado")
_Handler = socketio.get_tornado_handler(sio)

config = json.load(open("config/web.json"))
CORS_ORGINS = config["CORS_ORGINS"]
SESSION_TIMEOUT = config["session_timeout_length"]

async def redisSecConnection():
    try: # This Redis Index will be only for storage of security related items, like keys for examples
        redisDB = await aioredis.create_redis_pool(("localhost", 6379), encoding="utf-8", db=10)
        return redisDB
    except OSError as ex:
        print("Failed to connect to Redis, aborting action!")
        raise ex

class SocketHandler(_Handler):
    def check_origin(self, origin):
        if origin in CORS_ORGINS:
            return True
        else:
            return False

'''
Auth System Docs (Kinda?):
Values:
client_id: A HMAC signed random value that is sent to the client as an ID along with client_token
client_redis_token: A *unsigned* random base64 string that in a key value pair with the client_id
client_token: A HMAC signed version of the client_redis_token that is sent to the client along with the client_id
----------------------------------------------------------
Redis Auth Structure:
Hashmap Set: client_id: {plain_token: client_redis_token, plaid_id: client_plain_id}
----------------------------------------------------------
Registration Process:
When a user connects to the dashboard initally, the dashboard sends a socket registration message. The backend
responds and gives them a HMAC signed ID and Token. In Redis we store the unsigned version of both of these for
later verification. Now every message that the dashboard sends to the API must be authenticated with a JSON string
of {client_id: client_token} and these must match verification in order for the dashboard to send any specific data.
----------------------------------------------------------
Verification Process:
When a user sends a message to us requesting any data, it *MUST* be accompanied with a JSON string in the format of
{client_id: client_token}. Once we get this, we proceed to then lookup in Redis by the signed client_id. If this lookup fails, assume the
key to be tampered and force them to refresh their session to continue. To verify the user is who they are, use the plain_token and plain_id
from the Redis Hash Set and then HMAC these and compare the signatures to see if they match. If they do, we check what data that user wants
and if they can have it on the backend and then respond with it. If the signatures do not match, which means they were tampered with
we respond with a {ERROR: 403} and let the dashboard process it and inform the user their auth failed.
'''


class SocketNamespace(AsyncNamespace):
    HMAC_KEY = token_bytes(128)

    async def encode_key(self, key):
        return base64.urlsafe_b64encode(await self.sign_data(key)).decode("utf8")

    async def add_client(self):
        redisKeyDB = await redisSecConnection()

        client_redis_id = token_urlsafe(64)
        client_redis_token = token_urlsafe(64)

        client_id = await self.encode_key(client_redis_id)
        client_token = await self.encode_key(client_redis_token)

        auth_pipeline = redisKeyDB.pipeline()
        auth_pipeline.hmset_dict(client_id, {"plain_token": client_redis_token, "plain_id": client_redis_id}) # There is probably a more efficent way to do this
        auth_pipeline.expire(client_id, SESSION_TIMEOUT) # This will keep Redis clean :)
        await auth_pipeline.execute()
        redisKeyDB.close() # No leaking here

        return {"client_id":client_id, "client_token":client_token, "timestamp":time(), "status": "AUTH_SET"}

    async def sign_data(self, data):
        data = bytearray(data, encoding="utf8")
        signed_data = hmac.digest(self.HMAC_KEY, data, blake2b)
        return signed_data

    async def verify_client(self, userAuth): # TODO: Persistant HMAC Key in Redis
        redisKeyDB = await redisSecConnection()
        client_auth_entry = await redisKeyDB.hgetall(userAuth["client_id"])
        if client_auth_entry != []:
            client_expected_token = await self.encode_key(client_auth_entry["plain_token"])
            token_signature_match = hmac.compare_digest(userAuth["client_token"], client_expected_token)

            client_expected_id =  await self.encode_key(client_auth_entry["plain_id"])
            id_signature_match = hmac.compare_digest(userAuth["client_id"], client_expected_id)
 
            if id_signature_match == True and token_signature_match == True:
                return True
            else:
                return False
        else:
            return {"status": 403}
        

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


class APIMain(SocketNamespace):
    async def on_connect(self, sid, environ):
        print("A socket connected!")
        test = "hello: " + token_urlsafe(10)
        await self.emit("api_response",
            data = test
        )
    async def on_disconnect(self, sid):
        print("A socket disconnected!")

    async def on_register_client(self, sid, data):
        if data == None or data == "undefined":
            print("Registering a client...")
            signed_client_key = await self.add_client()
            await self.emit("api_response/registrationID", signed_client_key)
            print("Client registered!")
        else:
            if (time() - float(data)) > SESSION_TIMEOUT:
                print("Expired client session, renewing...")
                signed_client_key = await self.add_client()
                await self.emit("api_response/registrationID", signed_client_key)
                print("Client renewed!")
            else:
                await self.emit("api_response/registrationID", 
                    data = {"status": "OK"}
                )


# WebSocket Namespaces
from routes.api.guids import Guilds

sio.register_namespace(APIMain("/api/"))
sio.register_namespace(Guilds("/api/guilds"))