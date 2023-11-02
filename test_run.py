import discord
from discord.ext import commands
from pymongo import MongoClient
import os

### Configuration
client_token = os.environ.get('token')
db_url = os.environ.get('db_url')
db_name = os.environ.get('db_name')

### DB Connect
mango_url = 'mongodb+srv://{}/?retryWrites=true'.format(db_url)
cluster = MongoClient(mango_url)
db = cluster[db_name]
boss_list = []
boss_sub_list = []
primary_boss_dict = {}
secondary_boss_dict = {}
pending_message_list = []
user_db = cluster['Users']

leaderboards_channel_id = db['config'].find()[0]['leaderboard_id']
server_id = db['config'].find()[0]['server_id']

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='$',
            intents = discord.Intents.all(),
        )
        self.initial_extensions = [
            "cogs.leaderboard"
        ]
        self.loop.create_task(self.setup_hook())
    
    async def setup_hook(self):
        for ext in self.initial_extensions:
            self.load_extension(ext)
            #cog = self.get_cog(ext)
            #cog = self.get_cog("Leaderboard")
            #print(cog)
            #await self.load_extension(ext)
            #await cog.setup(server_id)
        await bot.tree.sync(guild=discord.Object(id=server_id))

bot = MyBot()
bot.run(client_token)