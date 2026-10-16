print("Starting...")

import os
import importlib
import sys
from dotenv import load_dotenv

import disnake
from disnake.ext import commands
from cogs.shared.sheets.sheet_manager import get_active_guild_ids
from cogs.shared.emotes.emotes import emote_guilds
from cogs.shared.pokemon import Pokemon

# Load variables from the .env file
load_dotenv(dotenv_path=".venv/.env")
bot_token = os.getenv("DISCORD_BOT_TOKEN")

print("  Packages loaded")

bot = commands.Bot(
    command_prefix=
    '!',  # not necessary given nothing here is currently using text commands
    intents=disnake.Intents.all(
    ),  # I should really update this to only have intents the bot actually uses....
    test_guilds=get_active_guild_ids())

@bot.event
async def on_ready():
    Pokemon.pass_guilds(list(filter(None, [bot.get_guild(guild_id) for guild_id in emote_guilds])))

    print(f'  We have logged in as {bot.user}')

print("Loading Cogs...")

modules_dir = "cogs"
sys.path.append(modules_dir)

for filename in os.listdir(modules_dir):
    if filename.endswith(".py"):
        module_name = filename[:-3]  # Strip the '.py' extension
        cog = importlib.import_module(module_name).Cog(bot)
        bot.add_cog(cog)
        print(f"  Loaded {cog.qualified_name}")


while True:
    print("Connecting to Discord...")
    bot.run(bot_token)