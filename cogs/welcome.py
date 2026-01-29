import discord
from discord.ext import commands
from datetime import datetime, timezone

from config import (
    WELCOME_CHANNEL_ID,
    RULES_CHANNEL_ID,
    PURCHASE_CHANNEL_ID,
    TICKET_CHANNEL_ID,
    VERIFICATION_CHANNEL_ID,
    MEMBER_ROLE_ID
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
            description=(
                "# <:hello:1466443612614295727> Приветствуем в Shiwo ac\n\n"
                f"{member.mention}, мы рады вас видеть!\n\n"
            ),
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(
            name="<:rules:1466443610646904934> Правила сервера",
            value=(
                f"Пожалуйста прочитайте {rules_channel.mention}\n"
                if rules_channel else
                "Пожалуйста прочитайте канал с правилами."
            ),
            inline=True
        )

        embed.add_field(
            name="<:price:1466443608709398669> Цены и оплата",
            value=(
                f"Посмотрите {purchase_channel.mention}\n"
                "для того чтобы ознакомиться с нашим предложением."
                if purchase_channel else
                "Ознакомьтесь с каналом наших предложений"
            ),
            inline=True
        )

        embed.add_field(
            name="<:help:1466443606435954758> Нужна помощь?",
            value=(
                f"Откройте тикет {ticket_channel.mention} и наша команда поможет вам."
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


RULES_TEXT = (
    "# SHIWO RULES\n\n"
    "## 1. Уважение\n\n"
    "Уважайте всех участников. Спорить и обсуждать можно любые темы — только вежливо.\n\n"
    "## 2. Запрещено: токсичность / расизм / харассмент\n\n"
    "Любые проявления ненависти, дискриминации и травли будут наказаны.\n\n"
    "## 3. Личная информация = бан\n\n"
    "Фото, имена, IP-адреса и любые конфиденциальные данные запрещены.\n"
    "Сразу и навсегда (PERM BAN).\n\n"
    "## 4. Не пингуйте Staff\n\n"
    "Нужна помощь? Открывайте тикет в <#1450569457259778078>\n\n"
    "## 5. Спам запрещён\n\n"
    "Флуд, спам, навязчивая реклама — запрещены.\n"
    "Для промо используйте только разрешённые способы/каналы.\n\n"
    "## 6. NSFW / Gore запрещены\n\n"
    "18+ контент, порно, жесть, кровь и т.п.\n"
    "Сразу и навсегда (PERM BAN).\n\n"
    "## 7. Запрещено злоупотреблять SHIWO Bot\n\n"
    "Любые попытки использовать бота во вред — перманентные санкции.\n\n"
    "## 8. Ознакомьтесь с правилами Discord\n\n"
    "## 9. Terms of Service\n\n"
    "https://shiwo-ac.com/au/tos\n\n"
    "Нарушение правил = наказание без предупреждения."
)


class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Принять правила",
        style=discord.ButtonStyle.green,
        custom_id="verify_accept_persistent",
        emoji="✅"
    )
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(MEMBER_ROLE_ID)
        if not role:
            return await interaction.response.send_message(
                "Роль не найдена на сервере.",
                ephemeral=True
            )

        member = interaction.user
        if role in member.roles:
            return await interaction.response.send_message(
                "У вас уже есть роль участника.",
                ephemeral=True
            )

        try:
            await member.add_roles(role, reason="Принятие правил сервера")
            await interaction.response.send_message(
                "✅ Вы успешно приняли правила и получили доступ к серверу.",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Ошибка: у бота недостаточно прав для выдачи роли.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Произошла ошибка: {e}",
                ephemeral=True
            )


class VerificationCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.add_view(VerifyView())
        self.panel_sent = False

    def build_rules_embed(self) -> discord.Embed:
        embed = discord.Embed(
            description=RULES_TEXT,
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text="Пожалуйста, примите правила для получения доступа к серверу")
        return embed

    @commands.Cog.listener()
    async def on_ready(self):
        if self.panel_sent:
            return
        
        self.panel_sent = True
        
        for guild in self.bot.guilds:
            channel = guild.get_channel(VERIFICATION_CHANNEL_ID)
            if not channel:
                print(f"[ВЕРИФИКАЦИЯ] Канал ID {VERIFICATION_CHANNEL_ID} не найден в {guild.name}")
                continue

            try:
                await channel.purge(limit=10)
                await channel.send(embed=self.build_rules_embed(), view=VerifyView())
                print(f"[ВЕРИФИКАЦИЯ] Панель создана в {guild.name}")
            except Exception as e:
                print(f"[ВЕРИФИКАЦИЯ] Ошибка создания панели: {e}")


async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))
    await bot.add_cog(VerificationCog(bot))
