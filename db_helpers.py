from pymongo import MongoClient
import pymongo

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
def add_boss(db, boss_id, boss_name, category_id, category_name, image_url, limit, color):
    entry = {
        '_id': boss_id,
        'name': boss_name,
        'categories': {category_id: {'index': 0, 'name': category_name, 'limit': limit}},
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
def add_boss_category(db, boss_id, category_id, category_name, limit):
    col = db['bosses']
    query = {"_id": boss_id}
    if col.count_documents(query) > 0:
        index = col.count_documents(query)
        update_entry = {'index': index, 'name': category_name, 'limit': limit}
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
def add_user(db, discord_id, rsn):
    col = db['discord_rsn']
    query = {"_id": discord_id}
    if col.count_documents(query) == 0:
        entry = {"_id": discord_id, "rsn": rsn}
        col.insert_one(entry)
        print('inserting rsn')
    else:
        print('rsn already exists')

def get_rsn(db, discord_id):
    query = {"_id": discord_id}
    rsn = db['discord_rsn'].find(query)[0]['rsn']
    return rsn

#################
#### RECORDS ####
#################

### Inputs or updates leaderboard time for a user
def write_record(db, boss_id, category_id, discord_id, seconds):
    data = {'seconds': seconds, 'pending': 1}
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
def add_time(db, boss_id, category_id, discord_id, seconds):
    message = 'Time Updated: {}|{}|{}|{}. Awaiting confirmation'.format(discord_id, boss_id, category_id, seconds)
    query = {'_id': boss_id, 'categories.{}'.format(category_id):{ "$exists": True }}
    if db.bosses.count_documents({"_id": boss_id}) > 0:
        print('Boss Exists')
        if db.bosses.count_documents(query) > 0:
            print('Boss Category Exists')
            write_record(db, boss_id, category_id, discord_id, seconds)
        else:
            print('Boss Category does not exist')
            message = 'Incorrect category_id. Check /boss for available bosses'
    else:
        print('Boss does not exist')
        message = 'Incorrect boss_id. Check /boss for available bosses'
    return message

### Removes pending state in db after approval
def remove_pending(db, boss_id, category_id, discord_id, seconds):
    boss_col = db[boss_id]
    query = {"_id": discord_id}
    boss_col.update_one(query, {"$set": {'{}.pending'.format(category_id): 0}})

### Gets top time for leaderboard where x is limit set in bosses collection
def get_top_x(db, boss_id, category_id):
    query = {"_id": boss_id}
    boss_col = db[boss_id]
    limit = db['bosses'].find(query)[0]['categories'][category_id]['limit']
    top_x = db[boss_id].find({"{}.pending".format(category_id):0}).sort("{}.seconds".format(category_id), pymongo.ASCENDING).limit(limit)
    return top_x
