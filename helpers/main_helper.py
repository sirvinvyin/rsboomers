### Stores boss list and boss category list into bot storage
def refresh_boss_list(db, bot):
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
    bot.boss_list = boss_list
    bot.boss_sub_list = boss_sub_list
    bot.primary_boss_dict = primary_boss_dict
    bot.secondary_boss_dict = secondary_boss_dict

def refresh_pending_messages(db, bot):
    pending_message_list = []
    for item in db['pending_times'].find():
        pending_message_list.append(item['_id'])
    pending_message_list = list(set(pending_message_list))
    bot.pending_message_list = pending_message_list