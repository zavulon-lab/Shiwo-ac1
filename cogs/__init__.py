import os
from discord.ext import commands

def load_all_cogs(bot: commands.Bot):
    for filename in os.listdir(os.path.dirname(__file__)):
        if filename.endswith(".py") and filename != "__init__.py":
            cog_name = f"cogs.{filename[:-3]}"
            try:
                bot.load_extension(cog_name)
                print(f"Ког загружен: {cog_name}")
            except Exception as e:
                print(f"Ошибка загрузки кога {cog_name}: {e}")