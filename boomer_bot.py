import discord
from pymongo import MongoClient
import db_helpers
from discord import app_commands
from typing import List
import os
from dotenv import load_dotenv
load_dotenv()

### Configuration
bot_user_id = 1049433791900422245
#bot_user_id = 960877380644270140
leaderboards_channel_id = 1108988733170143273
#leaderboards_channel_id = 1109111576562245722
server_id = '827233457226514442'
#server_id = '763051850785488906'

### Discord Connect
intents = discord.Intents.default()
intents.message_content = True
#bot = commands.Bot(command_prefix='!', intents=intents)
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
client_token = os.getenv("token")

### DB Connect
mango_url = os.getenv("db_url")
cluster = MongoClient(mango_url)
db = cluster["UserData"]
boss_list = []
boss_sub_list = []

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

def update_leaderboards(boss_id):
    boss_data = db.bosses.find({'_id': boss_id})[0]
    boss_title = boss_data['name']
    hex_int = int(boss_data['color'], base=16)
    embed = discord.Embed(title=boss_data['name'], description=None, color=hex_int)
    embed.set_thumbnail(url=boss_data['image'])
    for category_id in boss_data['categories']:
        description = boss_data['categories'][category_id]['name']
        if category_id == boss_id:
            description = "Top Times"
        rank = 1
        return_string = ""
        for i in db_helpers.get_top_x(db, boss_id, category_id):
            rsn = db_helpers.get_rsn(db, i['_id'])
            seconds = i[category_id]['seconds']
            m, s = divmod(seconds, 60)
            return_string+="{}. {}: {:02d}:{:02d}\n".format(rank, rsn, m, s)
            rank+=1
        embed.add_field(name=description, value=return_string, inline=False)
    return embed

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

@tree.command(name = "add_boss", description = "Add Boss", guild=discord.Object(id=server_id))
async def add_boss(interaction, boss_id: str, boss_name: str, category_id: str, category_name: str, image_url: str, limit: int, color: str):
    boss_response = db_helpers.add_boss(db, boss_id, boss_name, category_id, category_name, image_url, limit, color)
    hex_int = int(color, base=16)
    message = "Boss already exists"
    if boss_response == 1:
        message = "Boss added!"
        await interaction.response.send_message(message)
        embed = discord.Embed(title=boss_name, description=None, color=hex_int)
        embed.set_thumbnail(url=image_url)
        leaderboards_channel = client.get_channel(leaderboards_channel_id)
        message = await leaderboards_channel.send(embed=embed)
        db_helpers.update_boss(db, boss_id, 'message_id', message.id)
        refresh_boss_list()

@tree.command(name = "add_boss_category", description = "Add Boss Category", guild=discord.Object(id=server_id))
async def add_boss_category(interaction, boss_id: str, category_id: str, category_name: str, limit: int):
    boss_response = db_helpers.add_boss_category(db, boss_id, category_id, category_name, limit)
    message = "Boss does not exist. Enter boss via /add_boss command."
    if boss_response == 1:
        message = "Boss Updated!"
        refresh_boss_list()
    await interaction.response.send_message(message)

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

@tree.command(name = "add_rsn", description = "Add RSN", guild=discord.Object(id=server_id))
async def add_rsn(interaction, rsn: str, discord_id: str=None):
    if discord_id == None:
        discord_id = interaction.user.id
    else:
        discord_id = int(discord_id)
    db_helpers.add_user(db, discord_id, rsn)
    message = "RSN Added!"
    if db_helpers.check_id(db, discord_id) == 1:
        message = "RSN Updated!"
    await interaction.response.send_message(message)

@tree.command(name = "add_time", description = "Add Time", guild=discord.Object(id=server_id))
async def add_time(interaction, boss_id: str, category_id: str, minute: int, seconds: int, discord_id: str=None):
    seconds = minute*60+seconds
    if discord_id == None:
        discord_id = interaction.user.id
    else:
        discord_id = int(discord_id)
    if db_helpers.check_id(db, discord_id) == 1:
        message = db_helpers.add_time(db, boss_id, category_id, discord_id, seconds)
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


@client.event
async def on_raw_reaction_add(payload):
    #change this to list of approved user ids
    if payload.user_id != bot_user_id:
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
            db_helpers.remove_pending(db, boss_id, category_id, discord_id, seconds)
            await channel.send('Time Approved.')
            embed = update_leaderboards(boss_id)
            leaderboards_channel = client.get_channel(leaderboards_channel_id)
            boss_message_id = db['bosses'].find({'_id': boss_id})[0]['message_id']
            message = await leaderboards_channel.fetch_message(boss_message_id)
            await message.edit(embed=embed)
        elif str(payload.emoji) == '❌':
            await channel.send('Time Denied.')

reactions = ['✅', '❌']
@client.event
async def on_message(message):
    channel = message.channel
    if message.content.startswith('Time Updated') and message.author.id == bot_user_id:
        for reaction in reactions:
            await message.add_reaction(reaction)


@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=server_id))
    print("Ready!")

client.run(client_token)
