import discord
from pymongo import MongoClient
import leaderboards_helper
from discord import app_commands
from discord.ext import tasks
from typing import List
from itertools import cycle
import os
from datetime import datetime

### Configuration
#bot_user_id = 1049433791900422245
#leaderboards_channel_id = 1108988733170143273
#server_id = '827233457226514442'
bot_user_id = 960877380644270140
leaderboards_channel_id = 1109111576562245722
server_id = '763051850785488906'

approvers = [164199589614845952, 744266638857207878]

### Discord Connect
intents = discord.Intents.default()
intents.message_content = True
#bot = commands.Bot(command_prefix='!', intents=intents)
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
#client_token = os.getenv("token")
client_token = os.environ.get('token')
print(client_token)

### DB Connect
#mango_url = os.getenv("db_url")
db_data = os.environ.get('db_url')
mango_url = 'mongodb+srv://{}/?retryWrites=true'.format(db_data)
print(mango_url)
cluster = MongoClient(mango_url)
db = cluster["UserData"]
boss_list = []
boss_sub_list = []

# Owner - 735571256526504008
# Staff - 737466594783133777
def is_staff(interaction: discord.Interaction):
    True if (interaction.user.id == 735571256526504008 or interaction.user.id == 737466594783133777) else False

### Locally stored boss list and boss category list for dropdown options.
def refresh_boss_list():
    global boss_list
    global boss_sub_list
    boss_list = []
    boss_sub_list = []
    for boss in db['bosses'].find():
        boss_list.append(boss['_id'])
        for category in boss['categories']:
            boss_sub_list.append(category)

refresh_boss_list()
print(boss_list)
print(boss_sub_list)

### Help command. Probably should be expanded on.
@tree.command(name = "help", description = "help", guild=discord.Object(id=server_id))
async def help(interaction):
    embed = discord.Embed(title='Boss List', description="name | id", color=0x00FFFF)
    for boss in db['bosses'].find():
        boss_id = boss['_id']
        field_name = '{}: {}'.format(boss['name'], boss_id)
        boss_string = ''
        for category in boss['categories']:
            boss_string+='{}: {}\n'.format(boss['categories'][category]['name'], category)
        embed.add_field(name=field_name, value=boss_string, inline=False)
    await interaction.response.send_message(embed=embed)

### Add boss command.
# 1. Adds boss to db, 2. creates boss collection 3. creates placeholder message in leaderboards channel
@tree.command(name = "add_boss", description = "Add Boss", guild=discord.Object(id=server_id))
async def add_boss(interaction, boss_id: str, boss_name: str, category_id: str, category_name: str, image_url: str, limit: int, color: str):
    boss_response = leaderboards_helper.add_boss(db, boss_id, boss_name, category_id, category_name, image_url, limit, color)
    hex_int = int(color, base=16)
    message = "Boss already exists"
    if boss_response == 1:
        message = "Boss added!"
        await interaction.response.send_message(message)
        embed = discord.Embed(title=boss_name, description=None, color=hex_int)
        embed.set_thumbnail(url=image_url)
        leaderboards_channel = client.get_channel(leaderboards_channel_id)
        message = await leaderboards_channel.send(embed=embed)
        leaderboards_helper.update_boss(db, boss_id, 'message_id', message.id)
        refresh_boss_list()

### Add boss category command (eg. solo_cm, solo_normal for cox)
@tree.command(name = "add_boss_category", description = "Add Boss Category", guild=discord.Object(id=server_id))
async def add_boss_category(interaction, boss_id: str, category_id: str, category_name: str, limit: int):
    boss_response = leaderboards_helper.add_boss_category(db, boss_id, category_id, category_name, limit)
    message = "Boss does not exist. Enter boss via /add_boss command."
    if boss_response == 1:
        message = "Boss Updated!"
        refresh_boss_list()
    await interaction.response.send_message(message)

### Update boss command. Used to update boss metadata for example how many records are shown in leaderboard.
@tree.command(name = "update_boss", description = "Update Boss Metadata", guild=discord.Object(id=server_id))
async def add_boss_category(interaction, update_field: str, update_value: str):
    if update_field.str.contains('limit'):
        update_value = int(update_value)
    response = update_boss(db, boss_id, update_field, update_value)
    message = 'Boss does not exist. Enter boss via /add_boss command.'
    if response == 1:
        message = 'Boss Updated'
        refresh_boss_list()
    await interaction.response.send_message(message)

### Map rsn/preferred name to discord_id command. Required to enter time.
# Optional discord_id field allows another user to input a preferred name.
# TODO: maybe limit option to update another user based on permissions.
@tree.command(name = "add_rsn", description = "Add RSN", guild=discord.Object(id=server_id))
@app_commands.check(is_staff)
async def add_rsn(interaction, rsn: str, discord_id: str=None):
    if discord_id == None:
        discord_id = interaction.user.id
    else:
        discord_id = int(discord_id)
    leaderboards_helper.add_user(db, discord_id, rsn)
    message = "RSN Added!"
    if leaderboards_helper.check_id(db, discord_id) == 1:
        message = "RSN Updated!"
    await interaction.response.send_message(message)

### Adds time to database.
# TODO: update pending to be message_id instead of hardcoded 1. Use message_id when approving / declining.
@tree.command(name = "add_time", description = "Add Time", guild=discord.Object(id=server_id))
async def add_time(interaction, boss_id: str, category_id: str, minute: int, seconds: int, discord_id: str=None):
    seconds = minute*60+seconds
    if discord_id == None:
        discord_id = interaction.user.id
    else:
        discord_id = int(discord_id)
    if leaderboards_helper.check_id(db, discord_id) == 1:
        message = leaderboards_helper.add_time(db, boss_id, category_id, discord_id, seconds)
    else:
        message = "Enter RSN via /add_rsn command first."
    await interaction.response.send_message(message)

@add_time.autocomplete('boss_id')
async def boss_id_autocompletion(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    data = []
    for boss_id in boss_list:
        data.append(app_commands.Choice(name=boss_id, value=boss_id))
    return data

@add_time.autocomplete('category_id')
async def category_id_autocompletion(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    data = []
    for category_id in boss_sub_list:
        data.append(app_commands.Choice(name=category_id, value=category_id))
    return data

### Approval event for submitted time.
# TODO: limit approvers.
# TODO: get data from db instead of reading off of message string.
@client.event
@app_commands.check(is_staff)
async def on_raw_reaction_add(payload):
    if payload.user_id in approvers:
        guild = client.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        values = message.content.split(': ')[1].split('.')[0]
        list = values.split("|")
        print(list)
        if str(payload.emoji) == '✅':
            discord_id = int(list[0])
            boss_id = list[1]
            category_id = list[2]
            seconds = list[3]
            leaderboards_helper.remove_pending(db, boss_id, category_id, discord_id, seconds)
            await channel.send('Time Approved.')
            embed = leaderboards_helper.update_leaderboards(db, boss_id)
            leaderboards_channel = client.get_channel(leaderboards_channel_id)
            boss_message_id = db['bosses'].find({'_id': boss_id})[0]['message_id']
            message = await leaderboards_channel.fetch_message(boss_message_id)
            await message.edit(embed=embed)
        elif str(payload.emoji) == '❌':
            await channel.send('Time Denied.')

### Add emoji reactions to message.
# TODO: Can maybe use message_id instead of startswith if message_id is stored.
reactions = ['✅', '❌']
@client.event
async def on_message(message):
    channel = message.channel
    # Add Brown_Circle to Gold
    if message.author.id == 194285447206273025:
        message.add_reaction('brown_circle')
    if message.content.startswith('Time Updated') and message.author.id == bot_user_id:
        for reaction in reactions:
            await message.add_reaction(reaction)

# Keep Bot Alive
randomCycle = cycle(['Runescape', 'Runescape '])
@tasks.loop(seconds=500)
async def change_cycle():
    await client.change_presence(activity=discord.Game(next(randomCycle)))
    ### testing
    dt_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    test_channel = client.get_channel(1050135467603013653)
    test_message = await test_channel.fetch_message(1109628070329077780)
    await test_message.edit(content=dt_string)

@client.event
async def on_ready():
    change_cycle.start()
    await tree.sync(guild=discord.Object(id=server_id))
    print("Ready!")

client.run(client_token)
