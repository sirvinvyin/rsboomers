from discord.ext import commands
from discord_slash import cog_ext

class MyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @cog_ext.cog_slash(name="mycommand", description="This is my command")
    async def my_command(self, ctx):
        await ctx.send("Hello, Slash Command!")

def setup(bot):
    bot.add_cog(MyCog(bot))