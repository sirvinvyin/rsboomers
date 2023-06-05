import discord
from discord import app_commands
from discord.ext import commands

class Leaderboard(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot
    #self.server_id = None
  
  #async def setup(self, server_id):
  #  self.server_id = server_id
                
  @app_commands.command(name = "test", description = "This is a test")
  async def test(self, interaction: discord.Interaction, name: str, age: int):
    print("This is a test")

async def setup(bot: commands.Bot) -> None:
  #await bot.add_cog(Leaderboard(bot))
  await bot.add_cog(
    Leaderboard(bot),
    #guilds = bot.guilds
    guilds = [discord.Object(id=763051850785488906)]
  )

#
