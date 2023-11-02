from pymongo import MongoClient
import pymongo
import discord
import helpers.user_helper as user_helper
import math

################
#### BOSSES ####
################

### Add boss to database ####
# boss_id: Sluggified id for boss (eg. tob)
# boss_name: Display name of boss
# category_id: Sluggified sub-category of boss (eg. team_normal)
# category_name: Display name for sub-category of boss
# image_url: URL for image
# limit : Number of records shown in leaderboards
def add_boss(db, boss_id, boss_name, category_id, category_name, alias, image_url, limit, color):
    alias_entry = {'primary': alias, 'secondary': [alias]}
    entry = {
        '_id': boss_id,
        'name': boss_name,
        'categories': {category_id: {'index': 0, 'name': category_name, 'alias': alias_entry, 'limit': limit}},
        'image': image_url,
        'message_id': '',
        'color': color
    }
    col = db['bosses']
    query = {"_id": boss_id}
    if col.count_documents(query) == 0:
        col.insert_one(entry)
        db.create_collection(boss_id)
        return 1
    else:
        return 0

### Adds sub-category of existing boss
def add_boss_category(db, boss_id, category_id, category_name, alias, limit):
    col = db['bosses']
    alias_entry = {'primary': alias, 'secondary': [alias]}
    query = {"_id": boss_id}
    if col.count_documents(query) > 0:
        index = col.count_documents(query)
        update_entry = {'index': index, 'name': category_name, 'alias': alias_entry, 'limit': limit}
        col.update_one(query, {"$set": {'categories.{}'.format(category_id): update_entry}})
        boss_col = db[boss_id]
        return 1
    else:
        return 0

### Updates metadata for boss. Most useful for updating limit or image.
def update_boss(db, boss_id, update_field, update_value):
    col = db['bosses']
    query = {"_id": boss_id}
    if col.count_documents(query) > 0:
        col.update_one(query, {"$set": {update_field: update_value}})
        print('updating boss record')
    else:
        print('boss does not exist. Add boss first')

### Updates metadata for boss. Most useful for updating limit or image.
def add_alias(db, boss_id, category_id, alias):
    col = db['bosses']
    query = {"_id": boss_id}
    if col.count_documents(query) > 0:
        col.update_one(query, {"$push": {'categories.{}.alias.secondary'.format(category_id): alias}}, upsert=True)
        print('updating boss record')
    else:
        print('boss does not exist. Add boss first')

#####################
#### DISCORD_RSN ####
#####################

### Checks if the discord_id exists in DB. Needs to exist in order to enter time.
def check_id(db, discord_id):
    if db.discord_rsn.count_documents({"_id": discord_id}) > 0:
        print('exists')
        return 1
    else:
        print('enter_id')
        return 0

### Adds user to database. Used to map discord_id to preferred name.
### Will update if id exists already.
def add_user(user_db, discord_id, discord_name, rsn=None):
    col = user_db['discord_users']
    query = {"_id": discord_id}
    entry = {"_id": discord_id, "discord_name": discord_name, "rsn": rsn}
    if col.count_documents(query) == 0:
        col.insert_one(entry)
        print('inserting rsn')
    else:
        col.update_one(query, {"$set": entry})
        print('updating record')

def get_discord_name(user_db, discord_id):
    query = {"_id": discord_id}
    rsn = user_db['discord_users'].find(query)[0]['discord_name']
    return rsn

#################
#### RECORDS ####
#################

### Adds time to pending collection
def add_to_pending(db, boss_id, category_id, discord_id, seconds, message_id):
    entry = {
        "_id": message_id,
        "boss_id": boss_id,
        "category_id": category_id,
        "discord_id": discord_id,
        "seconds": seconds
    }
    db['pending_times'].insert_one(entry)

### Inputs or updates leaderboard time for a user
def write_record(db, boss_id, category_id, discord_id, seconds):
    data = {'seconds': seconds}
    entry = {
        "_id": discord_id,
        category_id: data
    }
    boss_col = db[boss_id]
    query = {"_id": discord_id}
    if boss_col.count_documents(query) == 0:
        boss_col.insert_one(entry)
        print('inserting user')
    else:
        boss_col.update_one(query, {"$set": {category_id: data}})
        print('updating record')

### Ensures boss exists in DB.
def add_time(db, boss_id, category_id, discord_id, seconds, message_id):
    message = 'Time Updated: {}|{}|{}|{}. Awaiting confirmation'.format(discord_id, boss_id, category_id, seconds)
    query = {'_id': boss_id, 'categories.{}'.format(category_id):{ "$exists": True }}
    if db.bosses.count_documents({"_id": boss_id}) > 0:
        print('Boss Exists')
        if db.bosses.count_documents(query) > 0:
            print('Boss Category Exists')
            write_record(db, boss_id, category_id, discord_id, seconds, message_id)
        else:
            print('Boss Category does not exist')
            message = 'Incorrect category_id. Check /boss for available bosses'
    else:
        print('Boss does not exist')
        message = 'Incorrect boss_id. Check /boss for available bosses'
    return message

### Gets top time for leaderboard where x is limit set in bosses collection
def get_top_x(db, boss_id, category_id):
    query = {"_id": boss_id}
    boss_col = db[boss_id]
    limit = db['bosses'].find(query)[0]['categories'][category_id]['limit']
    top_x = db[boss_id].find({category_id: {"$exists":True}}).sort("{}.seconds".format(category_id), pymongo.ASCENDING).limit(limit)
    return top_x

### Refreshes leaderboards
def update_leaderboards(db, user_db, boss_id):
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
        for i in get_top_x(db, boss_id, category_id):
            rsn = get_discord_name(user_db, i['_id'])
            seconds = i[category_id]['seconds']
            frac, whole = math.modf(seconds)
            m, s = divmod(whole, 60)
            print(frac)
            m = int(m)
            s = int(s)
            if frac == 0:
                d = "00"
            else:
                d = str(int(round(frac,2)*100))
            return_string+="{}. {}: {:02d}:{:02d}.{}\n".format(rank, rsn, m, s, d)
            rank+=1
        embed.add_field(name=description, value=return_string, inline=False)
    return embed
