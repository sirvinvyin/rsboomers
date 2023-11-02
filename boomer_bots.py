import discord
from discord.ext import commands
from pymongo import MongoClient
import os
from typing import Literal, Optional
import helpers.main_helper as main_helper

### Configuration
TOKEN = os.environ.get('token')
db_url = os.environ.get('db_url')
db_name = os.environ.get('db_name')

### Discord Connect
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
#tree = app_commands.CommandTree(client)

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


class ExampleBot(commands.Bot):
    def __init__(self):
        # initialize our bot instance, make sure to pass your intents!
        # for this example, we'll just have everything enabled
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )

        self.initial_extensions = [
            "cogs.leaderboard",
            "cogs.test"
        ]
    # the method to override in order to run whatever you need before your bot starts
    async def setup_hook(self):
        for ext in self.initial_extensions:
            await self.load_extension(ext)
        #await self.load_extension("cogs.test")

bot = ExampleBot()
bot.db = db
bot.user_db = user_db
bot.server_id = server_id
bot.leaderboards_channel_id = leaderboards_channel_id
main_helper.refresh_boss_list(db, bot)
main_helper.refresh_pending_messages(db, bot)
bot.approver_list = [164199589614845952, 744266638857207878]
bot.role_list = [735571256526504008, 737466594783133777, 968954059388240023]

@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()

        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

bot.run(TOKEN)