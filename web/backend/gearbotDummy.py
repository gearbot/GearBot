import asyncio
import json

import aioredis

config = json.load(open("config/web.json"))

redisCommChannelLookuptable = config["redisCommChannelsTable"]
positionToPermissionLookupTable = config["positionToPermissionLookupTable"]

# Figure out what to do with this soon:tm:
gearbotPermsData = {
    00000000000000: {
        0000000000: 9101
    }
}

class MainProcessor():
    def __init__(self):
        self.gearbot_loop = asyncio.new_event_loop()

        self.channelToFunctionLookupTable = {
            "dash_AuthRequests": self.processAuthRequest,
            "dash_AuthResponses": None,
            "dash_DataTransfer": self.processDataTransfer
        }

    async def dbconnect(self):
        try:
            return await aioredis.create_redis_pool(("localhost", 6379), encoding="utf-8", db=0)
        except OSError:
            print("Failed to connect to the Redis database, exiting!")
            return

    async def publisher(self, messages):
        redisPub = await self.dbconnect()
        for message in messages:
            real_channel_name = f"dash_{redisCommChannelLookuptable.get(str(message[0]))}"
            print(f"Publishing on {real_channel_name}: {message[1]}")
            await redisPub.publish_json(real_channel_name, message[1])


    async def listener(self, channel_name):
        redisListen = await self.dbconnect()
        full_channel_name = f"dash_{channel_name}"
        listen_channel = (await redisListen.subscribe(full_channel_name))[0]

        functionCall = self.channelToFunctionLookupTable.get(full_channel_name, None)
        if functionCall == None:
            return
        print(f"Spawned task for channel {channel_name}")
        while await listen_channel.wait_message():
            api_request = await listen_channel.get_json()
            await functionCall(api_request)
    
    async def processDataTransfer(self, data_transfer):
        print(data_transfer)
        return

    async def processAuthRequest(self, api_auth_request):
        redisDB = await self.dbconnect()
        authGetPipeline = redisDB.pipeline()
        
        userID = int(api_auth_request[0])
        userGuilds = api_auth_request[1]
        print(f"Request for user with ID of: {userID}")
        
        authStruct = []
        for guildID in userGuilds:
            print(f"Getting permissions for guildID : {guildID}")
            authGetPipeline.get(f"auth{userID}toguild{guildID}")
            authStruct.append([guildID])

        guildsAuthResults = await authGetPipeline.execute()
        i = 0
        for perms in guildsAuthResults:
            authStruct[i].append(perms)
            i += 1

        authSetPipeline = redisDB.pipeline()
        for authCheck in authStruct:
            guildID = int(authCheck[0])
            guildsPerms = authCheck[1]
            if guildsPerms != None: # This is if we already have perms stored for them
                await self.publisher([[2, [userID, guildID, int(guildsPerms)]]])
            else: # This is where we generate the permissions based on what Gearbot has recorded
                # We need an actual way to handle this later instead of test data. More of AE's thing here
                authSetPipeline.set(f"auth{userID}toguild{guildID}", gearbotPermsData[userID][guildID])
                #TODO: Return some of this data to the dashboard
                await self.publisher([[2, [userID, guildID, 9000]]]) # This means that the first view will show nothing until refresh
        print("-----------------------------")
        await authSetPipeline.execute()

print("Starting Dummy Gearbot!")
testProcess = MainProcessor()

for _, channel_name in redisCommChannelLookuptable.items():
    testProcess.gearbot_loop.create_task(testProcess.listener(channel_name))

testProcess.gearbot_loop.run_forever()