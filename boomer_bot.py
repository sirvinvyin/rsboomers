import discord
from pymongo import MongoClient
import leaderboards_helper
from discord import app_commands
from discord.ext import tasks
from typing import List
from itertools import cycle
import os
from datetime import datetime, timedelta
import modals

### Configuration
client_token = os.environ.get('token')
db_url = os.environ.get('db_url')
db_name = os.environ.get('db_name')

### Discord Connect
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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

# Owner - 735571256526504008
# Staff - 737466594783133777
approver_list = [164199589614845952, 744266638857207878]
role_list = [735571256526504008, 737466594783133777, 968954059388240023]
def is_staff(interaction: discord.Interaction):
    True if (interaction.user.id in approver_list) else False

### Locally stored boss list and boss category list for dropdown options.
def refresh_boss_list():
    global boss_list
    global boss_sub_list
    global primary_boss_dict
    global secondary_boss_dict
    boss_list = []
    boss_sub_list = []
    primary_boss_dict = {}
    secondary_boss_dict = {}
    for boss in db['bosses'].find():
        boss_id = boss['_id']
        boss_list.append(boss['_id'])
        for category in boss['categories']:
            print(category)
            category_id = category
            primary_alias = boss['categories'][category_id]['alias']['primary']
            input_dict = {"boss_id": boss_id, "category_id": category_id}
            primary_boss_dict[primary_alias] = input_dict
            for secondary_alias in boss['categories'][category_id]['alias']['secondary']:
                secondary_boss_dict[secondary_alias] = input_dict
            boss_sub_list.append(category)

def refresh_pending_messages():
    global pending_message_list
    pending_message_list = []
    for item in db['pending_times'].find():
        pending_message_list.append(item['_id'])
    pending_message_list = list(set(pending_message_list))

if db['bosses'].count_documents({})>0:
    refresh_boss_list()

refresh_pending_messages()


### Help command. Probably should be expanded on.
@tree.command(name = "help_leaderboard", description = "help", guild=discord.Object(id=server_id))
async def help_leaderboard(interaction):
    embed = discord.Embed(title='Leaderboard Commands for Boomer Bot', description="name | id", color=0x00FFFF)
    embed.add_field(name="/add_time", value="Adds time to leaderboard. Select boss from dropdown or can type to narrow, add time in min+seconds. Requires staff approval.", inline=False)
    embed.add_field(name="/add_rsn", value="Not required. Used for combat achievements. Will move this to combat achievements helper later.", inline=False)
    embed.add_field(name="/add_boss", value="Adds boss to database. Should be used to add any new bosses.", inline=False)
    embed.add_field(name="/add_boss_category", value="Adds category to boss. Eg. COX Solo CM, COX Team Normal", inline=False)
    embed.add_field(name="/add_alias", value="Adds alias to boss for search. Eg. Tombs of Amascut can have TOA as an alias", inline=False)
    embed.add_field(name="/update_boss", value="Used to update boss metadata. Requires familiarity with boss data structure. Eg. can change color of embed, # of records shown in leaderboard, boss name, etc", inline=False)
    embed.add_field(name="Boss Metadata", value="boss_id: sluggified id for boss (eg. toa), boss_name: display name (eg. Tombs of Amascut), category_id: slugified category of boss if applicable. Otherwise boss_id should be used, category_name: display name of category. alias: how the boss name+category should be shown to the user (eg. Tombs of Amascut (Expert - Solo)), image_url: url for image in embed. limit: number of records shown in highscore, color: embed color HEX format (eg. 0x808080)")
    await interaction.response.send_message(embed=embed)

### Add boss command.
# 1. Adds boss to db, 2. creates boss collection 3. creates placeholder message in leaderboards channel
@tree.command(name = "add_boss", description = "Add Boss", guild=discord.Object(id=server_id))
async def add_boss(interaction, boss_id: str, boss_name: str, category_id: str, category_name: str, alias: str, image_url: str, limit: int, color: str):
    boss_response = leaderboards_helper.add_boss(db, boss_id, boss_name, category_id, category_name, alias, image_url, limit, color)
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
async def add_boss_category(interaction, boss_id: str, update_field: str, update_value: str):
    if 'limit' in update_field:
        update_value = int(update_value)
    response = leaderboards_helper.update_boss(db, boss_id, update_field, update_value)
    message = 'Boss does not exist. Enter boss via /add_boss command.'
    if response == 1:
        message = 'Boss Updated'
        refresh_boss_list()
    await interaction.response.send_message(message)

### Update boss command. Used to update boss metadata for example how many records are shown in leaderboard.
@tree.command(name = "add_alias", description = "Add Alias to Boss", guild=discord.Object(id=server_id))
async def add_alias(interaction, boss_id: str, category_id: str, alias: str):
    leaderboards_helper.add_alias(db, boss_id, category_id, alias)
    refresh_boss_list()
    await interaction.response.send_message('Alias Added')

### Map rsn/preferred name to discord_id command. Required to enter time.
# Optional discord_id field allows another user to input a preferred name.
@tree.command(name = "add_rsn", description = "Add RSN", guild=discord.Object(id=server_id))
#@app_commands.check(is_staff)
async def add_rsn(interaction, rsn: str=None, discord_id: str=None):
    if discord_id == None:
        discord_id = interaction.user.id
        guild = await client.fetch_guild(server_id)
        user = await guild.fetch_member(discord_id)
        discord_name = user.nick
        if discord_name == None:
            discord_name = user.name
        leaderboards_helper.add_user(user_db, discord_id, discord_name, rsn)
        message = "RSN Added/Updated!"
    else:
        if (interaction.user.id in approver_list) or any(role.id in role_list for role in interaction.user.roles):
            discord_id = int(discord_id)
            guild = await client.fetch_guild(server_id)
            user = await guild.fetch_member(discord_id)
            discord_name = user.nick
            if discord_name == None:
                discord_name = user.name
            leaderboards_helper.add_user(user_db, discord_id, discord_name, rsn)
            message = "RSN Added/Updated!"
        else:
            message = "Cannot update another user's info."
    await interaction.response.send_message(message)

### Adds time to database.
@tree.command(name = "add_time", description = "Add Time", guild=discord.Object(id=server_id))
async def add_time(interaction, boss_name: str, minute: int, seconds: int):
    boss_id = secondary_boss_dict[boss_name]['boss_id']
    category_id = secondary_boss_dict[boss_name]['category_id']
    total_seconds = minute*60+seconds
    discord_id = interaction.user.id
    if leaderboards_helper.check_id(user_db, discord_id) == 0:
        guild = await client.fetch_guild(server_id)
        user = await guild.fetch_member(discord_id)
        discord_name = user.nick
        if discord_name == None:
            discord_name = user.name
        leaderboards_helper.add_user(user_db, discord_id, discord_name, None)
    submit_message = "Submitted time: {} min {} seconds for {} {}. Pending Approval".format(minute, seconds, boss_id, category_id)
    await interaction.response.send_message(submit_message)
    message = await interaction.original_response()
    reactions = ['✅', '❌']
    for reaction in reactions:
        await message.add_reaction(reaction)
    leaderboards_helper.add_to_pending(db, boss_id, category_id, discord_id, total_seconds, message.id)
    refresh_pending_messages()

@add_time.autocomplete('boss_name')
async def boss_id_autocompletion(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    data = []
    primary_boss_list = list(primary_boss_dict.keys())
    secondary_boss_list = list(secondary_boss_dict.keys())
    if current == '':  
        for boss_name in primary_boss_list:
            data.append(app_commands.Choice(name=boss_name, value=boss_name))
    else:
        for boss_name in secondary_boss_list:
            if current.lower() in boss_name.lower():
                data.append(app_commands.Choice(name=boss_name, value=boss_name))
    return data

### Adds time to database for another user.
@tree.command(name = "add_time_other", description = "Add Time For Another User", guild=discord.Object(id=server_id))
async def add_time_other(interaction, boss_name: str, minute: int, seconds: int, discord_id: str):
    boss_id = secondary_boss_dict[boss_name]['boss_id']
    category_id = secondary_boss_dict[boss_name]['category_id']
    total_seconds = minute*60+seconds
    discord_id = int(discord_id)
    if leaderboards_helper.check_id(user_db, discord_id) == 0:
        guild = await client.fetch_guild(server_id)
        user = await guild.fetch_member(discord_id)
        discord_name = user.nick
        if discord_name == None:
            discord_name = user.name
        leaderboards_helper.add_user(user_db, discord_id, discord_name, None)
    submit_message = "Submitted time: {} min {} seconds for {} {}. Pending Approval".format(minute, seconds, boss_id, category_id)
    await interaction.response.send_message(submit_message)
    message = await interaction.original_response()
    reactions = ['✅', '❌']
    for reaction in reactions:
        await message.add_reaction(reaction)
    leaderboards_helper.add_to_pending(db, boss_id, category_id, discord_id, total_seconds, message.id)
    refresh_pending_messages()

@add_time_other.autocomplete('boss_name')
async def boss_name_autocompletion(
    interaction: discord.Interaction,
    current: str
) -> List[app_commands.Choice[str]]:
    data = []
    primary_boss_list = list(primary_boss_dict.keys())
    secondary_boss_list = list(secondary_boss_dict.keys())
    if current == '':  
        for boss_name in primary_boss_list:
            data.append(app_commands.Choice(name=boss_name, value=boss_name))
    else:
        for boss_name in secondary_boss_list:
            if current.lower() in boss_name.lower():
                data.append(app_commands.Choice(name=boss_name, value=boss_name))
    return data

### Approval event for submitted time.
@client.event
async def on_raw_reaction_add(payload):
    if (payload.message_id in pending_message_list) and str(payload.emoji) in ['✅', '❌'] and (payload.user_id in approver_list or any(role.id in role_list for role in payload.member.roles)):
        guild = client.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        payload_message = await channel.fetch_message(payload.message_id)
        if str(payload.emoji) == '✅':
            data = db['pending_times'].find({"_id": payload.message_id})[0]
            leaderboards_helper.write_record(db, data['boss_id'], data['category_id'], data['discord_id'], data['seconds'])
            await channel.send('Time Approved.')
            embed = leaderboards_helper.update_leaderboards(db, user_db, data['boss_id'])
            leaderboards_channel = client.get_channel(leaderboards_channel_id)
            boss_message_id = db['bosses'].find({'_id': data['boss_id']})[0]['message_id']
            boss_message = await leaderboards_channel.fetch_message(boss_message_id)
            await boss_message.edit(embed=embed)
        elif str(payload.emoji) == '❌':
            await channel.send('Time Denied.')
        query = {"_id": payload.message_id}
        db['pending_times'].delete_many(query)
        await payload_message.delete()

### Add emoji reactions to message.
@client.event
async def on_message(message):
    channel = message.channel
    # Add Brown_Circle to Gold
    if message.author.id == 194285447206273025:
       await message.add_reaction('🟤')

@tree.command(name = "modal_test", description = "modal_testr", guild=discord.Object(id=server_id))
async def trymodal(interaction):
  modal = modals.MyModal(title = "Modal via Slash Command")
  await interaction.response.send_modal(modal)

# Keep Bot Alive
randomCycle = cycle(['Runescape', 'Runescape 3'])
@tasks.loop(seconds=400)
async def change_cycle():
    await client.change_presence(activity=discord.Game(next(randomCycle)))

@tree.command(name = "join_dates", description = "Join Dates", guild=discord.Object(id=server_id))
async def join_dates(interaction, days_back: int):
  today = datetime.datetime.now()
  compare_date = today - timedelta(days=days_back)
  message = ""
  for guild in client.guilds:                      
    for member in guild.members:                     
        message+=str(member.name)+' '+str(member.joined_at)+'\n'
  await interaction.response.send_message(message)


@client.event
async def on_ready():
    change_cycle.start()
    await tree.sync(guild=discord.Object(id=server_id))
    print("Ready!")

client.run(client_token)
