import json

from commands.RoleCommands import RoleCommand

versions = dict()

def initVersionInfo():
    try:
        with open('versions.json', 'r') as jsonfile:
            global versions
            versions = json.load(jsonfile)
    except FileNotFoundError:
        with open("versions.json", 'w') as jsonfile:
            initVersionInfo()
    except Exception as e:
        print(e)
        raise e

class addVersion(RoleCommand):
    def execute(self, client, channel, user, params):
        return super().execute(client, channel, user, params)