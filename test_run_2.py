from discord.ext import commands
import os

### Configuration
client_token = os.environ.get('token')

bot = commands.Bot(command_prefix="!")

# List of cog filenames or paths
cogs = ["cogs.test"]

# Load each cog
for cog in cogs:
    bot.load_extension(cog)

bot.run(client_token)