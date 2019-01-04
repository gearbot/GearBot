import aioredis

connection = None

def on_ready():
    try:
        connection = aioredis.create_connection()