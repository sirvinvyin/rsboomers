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