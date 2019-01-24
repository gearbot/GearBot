import aioredis
import asyncio
import json
import urllib
from secrets import token_urlsafe

from tornado import web, escape, routing
from tornado.web import removeslash, authenticated
from tornado.httpserver import HTTPServer
from tornado.httpclient import AsyncHTTPClient, HTTPRequest, HTTPClientError

import tornado.ioloop as ioloop
from tornado.options import parse_command_line

config = json.load(open("config.json"))

testing_userID = config["userIDForTestingCookie"]

client_id = config["clientID"]
client_secret = config["clientSecret"]
redirect_uri = config["redirect_uri"]

positionToPermissionLookupTable = config["positionToPermissionLookupTable"]
permissionsSchemaLookupTable = {v: k for k, v in positionToPermissionLookupTable.items()}
redisCommChannelLookuptable = config["redisCommChannelsTable"]


api_location = "https://discordapp.com/api/"

async def dbconnect():
    try:
        return await aioredis.create_redis_pool(("localhost", 6379), encoding="utf-8", db=0)
    except OSError:
        print("Failed to connect to the Redis database, exiting!")
        return

async def publishMessages(messages):
    redisComms = await dbconnect()
    for message in messages: # This allows us to send multiple if needed
        channelID = str(message[0])
        await redisComms.publish_json(f"dash_{redisCommChannelLookuptable.get(channelID)}", message[1])

async def authHandler(gearbotAuthResponse):
        userID = gearbotAuthResponse[0]
        guildID = gearbotAuthResponse[1]
        guildPerms = gearbotAuthResponse[2]

        if guildPerms != 9000:
            permissions = []
            guildPermissions = [guildID]
            position = 0
            for authValue in str(guildPerms):
                authValue = int(authValue)
                if authValue == 9: # Skip the header
                    position += 1
                else:
                    permissions.append((positionToPermissionLookupTable.get(str(position)), True if authValue != 0 else False))
                    position += 1

            guildPermissions.append([permissions])
            return guildPermissions
        else:
            return [guildID, None]

channelToFunctionLookupTable = {
    "dash_AuthResponses": authHandler
}

async def listener(listen_channel, expectedMessages):
    redisComms = await dbconnect()

    if type(listen_channel) == int:
        full_channel_name = f"dash_{redisCommChannelLookuptable.get(str(listen_channel))}"
    else:
        full_channel_name = f"dash_{listen_channel}"

    listeningChannel = (await redisComms.subscribe(full_channel_name))[0]
    responseData = []
    messageCount = 0
    while await listeningChannel.wait_message():
        gearbot_response = await listeningChannel.get_json()
        
        functionHandler = channelToFunctionLookupTable.get(full_channel_name, None)
        if functionHandler != None:
            response = await functionHandler(gearbot_response)
            responseData.append(response)
            messageCount += 1
            if messageCount == expectedMessages:
                return responseData


class PrimaryHandler(web.RequestHandler):

    requester = AsyncHTTPClient()

    user_refresh_tokens = {}

    def get_current_user(self):
        userIDCookie = self.get_secure_cookie("userauthtoken")
        if userIDCookie != None:
            return userIDCookie.decode()
        else:
            return None

    async def get_bearer_token(self, auth_code, isRefresh):
        if isRefresh != True:
            token_fetch = HTTPRequest(
                method = "POST",
                headers = {"Content-Type": "application/x-www-form-urlencoded"},
                body = urllib.parse.urlencode({
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "redirect_uri": redirect_uri,
                    "scope": "identify guilds"
                }),
                url = f"{api_location}/oauth2/token"
            )
        else:
            refresh_token = self.user_refresh_tokens[userID]
            token_fetch = HTTPRequest(
                method = "POST",
                headers = {"Content-Type": "application/x-www-form-urlencoded"},
                body = urllib.parse.urlencode({
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "redirect_uri": redirect_uri,
                    "scope": "identify guilds"
                }),
                url = f"{api_location}/oauth2/token"
            )
        try:
            token_return = await self.requester.fetch(token_fetch)
            access_token = escape.json_decode(token_return.body)["access_token"]
            refresh_token = escape.json_decode(token_return.body)["refresh_token"]
            userID = self.get_discorduser_info(access_token)
            self.user_refresh_tokens[userID] = refresh_token
            return access_token
        except HTTPClientError as error:
            if error.code == 401:
                print("OAuth error occured, we got a 401!")
                return 401
            else:
                print(f"An unexpected error occured with code: {error.code}")
                return error.code


    async def get_guild_list(self, token, userID):
        # The token can come back as none if this is called from a location we know it should be cached
        # This will need to reimplement the bearer token update Soon:TM: otherwise it will error out
        guilds_fetch = HTTPRequest(
            method = "GET",
            headers = {"Authorization": f"Bearer {token}"},
            url = f"{api_location}/users/@me/guilds"
        )
        try:
            redisDB = await dbconnect()
            redis_search_key = f"dash_userguilds{userID}"
            cached_guilds = await redisDB.get(redis_search_key)

            if cached_guilds != None or token == None:
                return cached_guilds
            else:
                guilds_return = await self.requester.fetch(guilds_fetch)

                guild_data_pipeline = redisDB.pipeline()
                guild_data_pipeline.set(redis_search_key, guilds_return.body)
                #guild_data_pipeline.expire(redis_search_key, 300)
                await guild_data_pipeline.execute()

                return guilds_return
        except HTTPClientError as error:
            if error.code == 401:
                access_token = await self.get_bearer_token(None, True)
                await self.get_guild_list(access_token)
                return
            else:
                print(f"An unexpected error occured with code: {error.code}")
                return error.code

    async def get_discorduser_info(self, token):
        user_fetch = HTTPRequest(
            method = "GET",
            headers = {"Authorization": f"Bearer {token}"},
            url = f"{api_location}/users/@me"
        )

        try:
            user_return = await self.requester.fetch(user_fetch)
            userID = escape.json_decode(user_return.body)["id"]
            return userID
        except HTTPClientError as error:
            if error.code == 401:
                access_token = await self.get_bearer_token(None, True)
                await self.get_discorduser_info(access_token)
                return
            else:
                print(f"An unexpected error occured with code: {error.code}")
                return error.code

    async def get_guilds_perms(self, userID):
        guild_list = escape.json_decode(await self.get_guild_list(None, userID))

        guild_ids = []
        for guild in guild_list:
            guild_ids.append(guild["id"])
        print(f"Sending AuthChecks for user: {userID}")

        await publishMessages([[1, (userID, guild_ids)]])
        apiResponse = await listener(listen_channel = 2, expectedMessages = (len(guild_list))) # Gearbot will respond with exactly the same amount we sent

        allGuildPerms = [userID]
        for guildAuthData in apiResponse:
            guildID = guildAuthData[0]
            guildPerms = guildAuthData[1]
            if guildPerms == None:
                pass
            else:
                permissionsToCheck = [item for sublist in guildPerms for item in sublist]
                grantedPermissions = []
                for permission in permissionsToCheck:
                    grantedPermissions.append(permission[0] if permission[1] != False else None)
                allGuildPerms.append((guildID, grantedPermissions))
        return allGuildPerms

# API structures
class MainAppPage(PrimaryHandler):
    @removeslash
    async def get(self):
        self.write("Welcome to the Gearbot Dashboard info page")
        self.finish()
        return

class DiscordOAuthRedir(PrimaryHandler): 
    @removeslash
    async def get(self):
        self.redirect(
            permanent = True,
            url = f"{api_location}/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20guilds"
        )
        return

class DiscordOAuthCallback(PrimaryHandler):
    @removeslash
    async def get(self):
        auth_code = self.get_query_argument("code")
        
        bearer_token = await self.get_bearer_token()
        
        userID = await self.get_discorduser_info(bearer_token)
        await self.get_guild_list(bearer_token, userID) # Puts the data in the cache

        self.set_secure_cookie(
            name = "userauthtoken",
            value = str(userID)
        )

        self.redirect("/dashboard")
        return

class GearbotDashboard(PrimaryHandler):
    @authenticated
    @removeslash
    async def get(self):
        userID = self.get_current_user()
        if userID == None:
            self.redirect("/discordlogin")
            return

        perm_data = await self.get_guilds_perms(userID)
        print("This is the perm data!: " + str(perm_data))
        self.write("Done")
        self.finish()
        return

class FrontendAPIGuildInfo(PrimaryHandler):
    @authenticated
    @removeslash
    async def post(self):
        userID = self.get_current_user()
        guild_perms_data = await self.get_guilds_perms(userID)
        self.write(escape.json_encode(guild_perms_data))
        self.finish()
        return

class AuthSetTestingEndpoint(PrimaryHandler):
    @removeslash
    async def get(self):
        self.set_secure_cookie(
            name = "userauthtoken",
            value = testing_userID
        )
        self.write("Auth cookie set!")
        return

class AuthGetTestingEndpoint(PrimaryHandler):
    @removeslash
    async def get(self):
        auth_id = self.get_secure_cookie("userauthtoken")
        if auth_id != None:
            self.write(f"Auth cookie is: {auth_id.decode()}")
        else:
            self.write("Auth cookie is invalid, please try again!")
        self.finish()
        return

class TestingCode(PrimaryHandler):
    @removeslash
    async def get(self):
        self.write("Testing page reached")
        self.finish()
        return

web_settings = {
    "cookie_secret": "4gjw63g34th3", #token_urlsafe(32),
    "login_url": "/discordlogin",
    "xsrf_cookies": False # Turn on when not testing
}

dashboardAPI = web.Application([
    (r"/", MainAppPage),
    (r"/discordlogin", DiscordOAuthRedir),
    (r"/discord/callback", DiscordOAuthCallback),
    (r"/dashboard", GearbotDashboard),
    (r"/setauth", AuthSetTestingEndpoint),
    (r"/checkauth", AuthGetTestingEndpoint),
    (r"/testing", FrontendAPIGuildInfo)
], **web_settings, debug=True)

print("Starting Gearbot Dashboard")

dashboard_server = HTTPServer(dashboardAPI) # Create the Tornado server
parse_command_line()
dashboard_server.listen(5000)

ioloop.IOLoop.current().start() # Start the primary event loop
