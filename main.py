import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv


load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ALLOWED_GUILD_ID = int(os.getenv("GUILD_ID", 0))


intents = discord.Intents.default()
intents.members = True
intents.message_content = True


bot = commands.Bot(command_prefix="!", intents=intents)


async def load_cogs():
    try:
        await bot.load_extension("cogs.tickets")
        print("Ког tickets загружен")
    except Exception as e:
        print(f"Ошибка загрузки tickets: {e}")
    try:
        await bot.load_extension("cogs.giveaway")
        print("Ког giveaway загружен")
    except Exception as e:
        print(f"Ошибка загрузки giveaway: {e}")
    try:
        await bot.load_extension("cogs.welcome")
        print("Ког welcome загружен")
    except Exception as e:
        print(f"Ошибка загрузки welcome: {e}")
    try:
        await bot.load_extension("cogs.protection")
        print("Ког protection загружен")
    except Exception as e:
        print(f"Ошибка загрузки protection: {e}")
    try:
        await bot.load_extension("cogs.clients")
        print("Ког clients загружен")
    except Exception as e:
        print(f"Ошибка загрузки clients: {e}")
    try:
        await bot.load_extension("cogs.user_logs")
        print("Ког user_logs загружен")
    except Exception as e:
        print(f"Ошибка загрузки user_logs: {e}")

    print("Все коги успешно загружены.")


@bot.event
async def on_ready():
    print(f"Бот {bot.user} успешно запущен!")
    
    await asyncio.sleep(2)

    guild = bot.get_guild(ALLOWED_GUILD_ID)
    
    if not guild:
        print(f"Сервер с ID {ALLOWED_GUILD_ID} не найден!")
        return
    
    print(f"\n[{guild.name}] Инициализирую панели...")
    
    tickets_cog = bot.get_cog("TicketsCog")
    if tickets_cog:
        try:
            await tickets_cog.setup_ticket_panel()
            if hasattr(tickets_cog, 'setup_admin_stats_panel'):
                await tickets_cog.setup_admin_stats_panel()
            print(f"  Tickets панель инициализирована")
        except Exception as e:
            print(f"  Ошибка Tickets: {e}")
    
    giveaway_cog = bot.get_cog('GiveawayCog')
    if giveaway_cog:
        try:
            await giveaway_cog.setup_giveaway_panels(guild)
            print(f"  Giveaway панель инициализирована")
        except Exception as e:
            print(f"  Ошибка Giveaway: {e}")
    
    protection_cog = bot.get_cog("ProtectionCog")  
    if protection_cog:
        try:
            await protection_cog.setup_protection_panel()
            print(f"  Protection панель инициализирована")
        except Exception as e:
            print(f"  Ошибка Protection: {e}")

    print("\nВсе панели настроены!\n")


async def main():
    async with bot:
        await load_cogs()
        await bot.start(DISCORD_TOKEN)


asyncio.run(main())