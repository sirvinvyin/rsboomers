import discord
from discord import app_commands
from discord.ext import commands
import helpers.main_helper as main_helper
import helpers.user_helper as user_helper
import helpers.leaderboard_helper as leaderboard_helper
from typing import List

# all cogs inherit from this base class
class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot # adding a bot attribute for easier access

    ### Help command. Probably should be expanded on.
    @app_commands.command(name = "help_leaderboard", description = "help")
    async def help_leaderboard(self, interaction):
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
    @app_commands.command(name = "add_boss", description = "Add Boss")
    async def add_boss(self, interaction, boss_id: str, boss_name: str, category_id: str, category_name: str, alias: str, image_url: str, limit: int, color: str):
        boss_response = leaderboard_helper.add_boss(self.bot.db, boss_id, boss_name, category_id, category_name, alias, image_url, limit, color)
        hex_int = int(color, base=16)
        message = "Boss already exists"
        if boss_response == 1:
            message = "Boss added!"
            await interaction.response.send_message(message)
            embed = discord.Embed(title=boss_name, description=None, color=hex_int)
            embed.set_thumbnail(url=image_url)
            leaderboards_channel = interaction.client.get_channel(self.bot.leaderboards_channel_id)
            message = await leaderboards_channel.send(embed=embed)
            leaderboard_helper.update_boss(self.bot.db, boss_id, 'message_id', message.id)
            main_helper.refresh_boss_list(self.bot.db, self.bot)
            print(self.bot.boss_list)
        else:
          await interaction.response.send_message(message)

    ### Add boss category command (eg. solo_cm, solo_normal for cox)
    @app_commands.command(name = "add_boss_category", description = "Add Boss Category")
    async def add_boss_category(self, interaction, boss_id: str, category_id: str, category_name: str, alias: str, limit: int):
        boss_response = leaderboard_helper.add_boss_category(self.bot.db, boss_id, category_id, category_name, alias, limit)
        message = "Boss does not exist. Enter boss via /add_boss command."
        if boss_response == 1:
            message = "Boss Updated!"
            main_helper.refresh_boss_list(self.bot.db, self.bot)
        await interaction.response.send_message(message)

    ### Update boss command. Used to update boss metadata for example how many records are shown in leaderboard.
    @app_commands.command(name = "update_boss", description = "Update Boss Metadata")
    async def update_boss(self, interaction, boss_id: str, update_field: str, update_value: str):
        if 'limit' in update_field:
            update_value = int(update_value)
        response = leaderboard_helper.update_boss(self.bot.db, boss_id, update_field, update_value)
        message = 'Boss does not exist. Enter boss via /add_boss command.'
        if response == 1:
            message = 'Boss Updated'
            main_helper.refresh_boss_list(self.bot.db, self.bot)
        await interaction.response.send_message(message)

    ### Update boss command. Used to update boss metadata for example how many records are shown in leaderboard.
    @app_commands.command(name = "add_alias", description = "Add Alias to Boss")
    async def add_alias(self, interaction, boss_id: str, category_id: str, alias: str):
        response = leaderboard_helper.add_alias(self.bot.db, boss_id, category_id, alias)
        message = "Boss/Boss category does not exist."
        if response == 1:
          message = "Alias Added"
          main_helper.refresh_boss_list(self.bot.db, self.bot)
        await interaction.response.send_message(message)

    ### Adds time to database.
    @app_commands.command(name = "add_time", description = "Add Time")
    async def add_time(self, interaction, boss_name: str, minute: int, seconds: float):
        boss_id = self.bot.secondary_boss_dict[boss_name]['boss_id']
        category_id = self.bot.secondary_boss_dict[boss_name]['category_id']
        total_seconds = minute*60+seconds
        discord_id = interaction.user.id
        if user_helper.check_id(self.bot.user_db, discord_id) == 0:
            guild = await self.bot.fetch_guild(self.bot.server_id)
            user = await guild.fetch_member(discord_id)
            discord_name = user.nick
            if discord_name == None:
                discord_name = user.name
            user_helper.add_user(self.bot.user_db, discord_id, discord_name, None)
        submit_message = "Submitted time: {} min {} seconds for {} {}. Pending Approval".format(minute, seconds, boss_id, category_id)
        await interaction.response.send_message(submit_message)
        message = await interaction.original_response()
        reactions = ['✅', '❌']
        for reaction in reactions:
            await message.add_reaction(reaction)
        leaderboard_helper.add_to_pending(self.bot.db, boss_id, category_id, discord_id, total_seconds, message.id)
        main_helper.refresh_pending_messages(self.bot.db, self.bot)

    @add_time.autocomplete('boss_name')
    async def boss_id_autocompletion(self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        data = []
        primary_boss_list = list(self.bot.primary_boss_dict.keys())
        print(primary_boss_list)
        secondary_boss_list = list(self.bot.secondary_boss_dict.keys())
        print(secondary_boss_list)
        if current == '':  
            for boss_name in primary_boss_list:
                print(boss_name)
                data.append(app_commands.Choice(name=boss_name, value=boss_name))
        else:
            for boss_name in secondary_boss_list:
                print(boss_name)
                if current.lower() in boss_name.lower():
                    data.append(app_commands.Choice(name=boss_name, value=boss_name))
        return data
  
    ### Adds time to database for another user.
    @app_commands.command(name = "add_time_other", description = "Add Time For Another User")
    async def add_time_other(self, interaction, boss_name: str, minute: int, seconds: float, discord_id: str):
        boss_id = self.bot.secondary_boss_dict[boss_name]['boss_id']
        category_id = self.bot.secondary_boss_dict[boss_name]['category_id']
        total_seconds = minute*60+seconds
        discord_id = int(discord_id)
        if user_helper.check_id(self.bot.user_db, discord_id) == 0:
            guild = await self.bot.fetch_guild(self.bot.server_id)
            user = await guild.fetch_member(discord_id)
            discord_name = user.nick
            if discord_name == None:
                discord_name = user.name
            user_helper.add_user(self.bot.user_db, discord_id, discord_name, None)
        submit_message = "Submitted time: {} min {} seconds for {} {}. Pending Approval".format(minute, seconds, boss_id, category_id)
        await interaction.response.send_message(submit_message)
        message = await interaction.original_response()
        reactions = ['✅', '❌']
        for reaction in reactions:
            await message.add_reaction(reaction)
        leaderboard_helper.add_to_pending(self.bot.db, boss_id, category_id, discord_id, total_seconds, message.id)
        main_helper.refresh_pending_messages(self.bot.db, self.bot)

    @add_time_other.autocomplete('boss_name')
    async def boss_name_autocompletion(self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        data = []
        primary_boss_list = list(self.bot.primary_boss_dict.keys())
        print(primary_boss_list)
        secondary_boss_list = list(self.bot.secondary_boss_dict.keys())
        print(secondary_boss_list)
        if current == '':  
            for boss_name in primary_boss_list:
                print(boss_name)
                data.append(app_commands.Choice(name=boss_name, value=boss_name))
        else:
            for boss_name in secondary_boss_list:
                print(boss_name)
                if current.lower() in boss_name.lower():
                    data.append(app_commands.Choice(name=boss_name, value=boss_name))
        return data
  
    ### Approval event for submitted time.
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if (payload.message_id in self.bot.pending_message_list) and str(payload.emoji) in ['✅', '❌'] and (payload.user_id in self.bot.approver_list or any(role.id in self.bot.role_list for role in payload.member.roles)):
            guild = await self.bot.fetch_guild(self.bot.server_id)
            channel = self.bot.get_channel(payload.channel_id)
            payload_message = await channel.fetch_message(payload.message_id)
            print(payload_message)
            if str(payload.emoji) == '✅':
                data = self.bot.db['pending_times'].find({"_id": payload.message_id})[0]
                leaderboard_helper.write_record(self.bot.db, data['boss_id'], data['category_id'], data['discord_id'], data['seconds'])
                await channel.send('Time Approved.')
                embed = leaderboard_helper.update_leaderboards(self.bot.db, self.bot.user_db, data['boss_id'])
                leaderboards_channel = self.bot.get_channel(self.bot.leaderboards_channel_id)
                boss_message_id = self.bot.db['bosses'].find({'_id': data['boss_id']})[0]['message_id']
                boss_message = await leaderboards_channel.fetch_message(boss_message_id)
                await boss_message.edit(embed=embed)
            elif str(payload.emoji) == '❌':
                await channel.send('Time Denied.')
            query = {"_id": payload.message_id}
            self.bot.db['pending_times'].delete_many(query)
            await payload_message.delete()

    # doing something when the cog gets loaded
    async def cog_load(self):
        print(f"{self.__class__.__name__} loaded!")

    # doing something when the cog gets unloaded
    async def cog_unload(self):
        print(f"{self.__class__.__name__} unloaded!")

# usually you’d use cogs in extensions
# you would then define a global async function named 'setup', and it would take 'bot' as its only parameter
async def setup(bot):
    # finally, adding the cog to the bot
    await bot.add_cog(LeaderboardCog(bot=bot))
