import discord
from discord.ext import commands
from datetime import datetime, timezone

from config import (
    WELCOME_CHANNEL_ID,
    RULES_CHANNEL_ID,
    PURCHASE_CHANNEL_ID,
    TICKET_CHANNEL_ID
)


class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            print(f"[ПРИВЕТСТВИЕ] Канал приветствий (ID: {WELCOME_CHANNEL_ID}) не найден!")
            return

        rules_channel = self.bot.get_channel(RULES_CHANNEL_ID)
        purchase_channel = self.bot.get_channel(PURCHASE_CHANNEL_ID)
        ticket_channel = self.bot.get_channel(TICKET_CHANNEL_ID)

        embed = discord.Embed(
            title="```Приветствуем в Shiwo Scanner```",
            description=(
                f"{member.mention}, мы рады вас видеть!\n\n"
                "Shiwo- это мощный сканер разработанный для того чтобы дать вам:\n"
                "**скорость, точность и надёжность.**\n\n"
                "Загляните в наши основные каналы "
            ),
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="Правила сервера",
            value=(
                f"Пожалуйста прочитайте {rules_channel.mention}\n"
                "чтобы сохранить комьюнити безопасным и дружелюбным."
                if rules_channel else
                "Пожалуйста прочитайте канал с правилами."
            ),
            inline=True
        )

        embed.add_field(
            name="Цены и оплата",
            value=(
                f"Посмотрите {purchase_channel.mention}\n"
                "для того чтобы ознакомиться с нашим предложением."
                if purchase_channel else
                "Ознакомьтесь с каналом наших предложений"
            ),
            inline=True
        )

        embed.add_field(
            name="Нужна помощь?",
            value=(
                f"Откройте тикет {ticket_channel.mention} и наша команда пошожет вам."
                if ticket_channel else
                "Загляните в канал поддержки."
            ),
            inline=False
        )

        embed.set_footer(
            text=f"User ID: {member.id} • Shiwo ac",
            icon_url=member.display_avatar.url
        )

        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))