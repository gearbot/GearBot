import json
import urllib

import aioredis
from tornado import escape
from tornado.httpclient import HTTPRequest, HTTPClientError, AsyncHTTPClient

API_LOCATION = "https://discordapp.com/api/"
CLIENT_ID = None
REDIRECT_URI = None

TESTING_USERID = None
CLIENT_SECRET = None
REDIS_CONNECTION = None
MESSAGER = None
REQUESTER = AsyncHTTPClient()


async def initialize(messager):
    global config, CLIENT_ID, TESTING_USERID, CLIENT_SECRET, REDIS_CONNECTION, MESSAGER, REDIRECT_URI
    with open("config/web.json") as file:
        config = json.load(file)
    TESTING_USERID = config["userIDForTestingCookie"]
    CLIENT_ID = config["clientID"]
    CLIENT_SECRET = config["clientSecret"]
    REDIRECT_URI = config["redirect_uri"]
    MESSAGER = messager

    try:
        REDIS_CONNECTION = await aioredis.create_redis_pool(("localhost", 6379), encoding="utf-8", db=0)
        await MESSAGER.initialize()
    except OSError as ex:
        print("Failed to connect to the Redis database, exiting!")
        raise ex


async def get_bearer_token(*, auth_code=None, user_id=None, refresh):
    # TODO: handle an attempted refresh where the auth code in storage expired
    if refresh:
        key = f"discord_refresh_token:{user_id}"
        code = await REDIS_CONNECTION.get(key)

    else:
        code = auth_code
    body = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token" if refresh else "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds"
    })
    print(body)
    token_fetch = HTTPRequest(
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=body,
        url=f"{API_LOCATION}/oauth2/token"
    )
    try:
        token_return = await REQUESTER.fetch(token_fetch)
        access_token = escape.json_decode(token_return.body)["access_token"]
        refresh_token = escape.json_decode(token_return.body)["refresh_token"]

        pipeline = REDIS_CONNECTION.pipeline()
        key = f"discord_refresh_token:{user_id}"
        pipeline.set(key, refresh_token)
        pipeline.expire(key, 24 * 60 * 60)
        await pipeline.execute()

        return access_token
    except HTTPClientError as error:
        if error.code == 401:
            print("OAuth error occured, we got a 401!")
            return 401
        else:
            print(f"An unexpected error occured with code: {error.code}")
            return error.code


async def get_guild_list(user_id, *, token = None):
    # The token can come back as none if this is called from a location we know it should be cached
    # This will need to reimplement the bearer token update Soon:TM: otherwise it will error out
    guilds_fetch = HTTPRequest(
        method = "GET",
        headers = {"Authorization": f"Bearer {token}"},
        url = f"{API_LOCATION}/users/@me/guilds"
    )
    try:
        redis_search_key = f"dash_user_guilds:{user_id}"
        cached_guilds = await REDIS_CONNECTION.get(redis_search_key)

        if cached_guilds is not None or token is None:
            return cached_guilds
        else:
            guilds_return = await REQUESTER.fetch(guilds_fetch)

            guild_data_pipeline = REDIS_CONNECTION.pipeline()
            guild_data_pipeline.set(redis_search_key, guilds_return.body)
            # guild_data_pipeline.expire(redis_search_key, 300)
            await guild_data_pipeline.execute()

            return guilds_return
    except HTTPClientError as error:
        if error.code == 401:
            access_token = await get_bearer_token(user_id=user_id, refresh=True)
            await get_guild_list(user_id, token=access_token)
            return
        else:
            print(f"An unexpected error occured with code: {error.code}")
            return error.code


async def get_user_id(token):
    user_fetch = HTTPRequest(
        method="GET",
        headers={"Authorization": f"Bearer {token}"},
        url=f"{API_LOCATION}/users/@me"
    )

    try:
        user_return = await REQUESTER.fetch(user_fetch)
        userID = escape.json_decode(user_return.body)["id"]
        return userID
    except HTTPClientError as error:
        if error.code == 401:
            access_token = await get_bearer_token(auth_code=token, refresh=True)
            return await get_user_id(access_token)
        else:
            print(f"An unexpected error occured with code: {error.code}")
            return error.code


async def get_guilds_info(user_id):
    guild_list = escape.json_decode(await get_guild_list(user_id))

    guild_ids = []
    for guild in guild_list:
        guild_ids.append(guild["id"])
    print(f"Sending AuthChecks for user: {user_id}")


    # TODO: caching?
    info = await MESSAGER.get_reply(dict(type="guild_perm_request", guild_list=guild_ids, user_id=user_id))
    return info
