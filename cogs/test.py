from discord import app_commands
from discord.ext import commands

# all cogs inherit from this base class
class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot # adding a bot attribute for easier access
    
    # adding a slash command to the cog (make sure to sync this!)
    @app_commands.command(name="ping")
    async def ping(self, interaction, name: str):
        """the second best command in existence"""
        await interaction.response.send_message(interaction.user.mention)

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
    await bot.add_cog(ExampleCog(bot=bot))