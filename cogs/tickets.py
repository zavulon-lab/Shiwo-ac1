import discord
import time
import io
import os
import json
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button, Select
from discord import (
    Interaction,
    ButtonStyle,
    SelectOption,
    PermissionOverwrite,
    CategoryChannel,
    TextChannel,
    Color
)
from datetime import datetime, timezone
import asyncio

from config import (
    TICKET_CHANNEL_ID,
    TICKET_CATEGORY_ID,
    TICKET_LOG_CHANNEL_ID,
    SUPPORT_ROLE_ID, 
    ADMIN_PANEL_CHANNEL_ID
)
STATS_FILE = "support_stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_stats(data):
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Загружаем данные при запуске
SUPPORT_STATS = load_stats()

class TicketCloseView(View):
    def __init__(self, ticket_channel: TextChannel, opener: discord.Member):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.opener = opener

    @discord.ui.button(label="Закрыть", style=ButtonStyle.red)
    async def close_ticket(self, interaction: Interaction, button: Button):
        if not (interaction.user.guild_permissions.administrator or interaction.user == self.opener):
            return await interaction.response.send_message("У вас нет прав!", ephemeral=True)

        await interaction.response.defer()

        # 1. Генерация данных (Транскрипт + Статистика сообщений)
        html_data = await generate_html_transcript(self.ticket_channel)
        
        stats = {}
        async for msg in self.ticket_channel.history(limit=None):
            if not msg.author.bot:
                stats[msg.author.display_name] = stats.get(msg.author.display_name, 0) + 1
        participants_text = "\n".join([f"{n} - {c} сообщений " for n, c in stats.items()]) or "Нет сообщений"

        # 2. ОТПРАВКА В АРХИВ (Админ-канал)
        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            file = discord.File(io.BytesIO(html_data.encode('utf-8')), filename=f"archive-{self.ticket_channel.name}.html")
            log_embed = discord.Embed(
                title="Архив тикета",
                description=f"**Канал:** `{self.ticket_channel.name}`\n**Закрыл:** {interaction.user.mention} ({interaction.user.id})\n**Причина:** Без указания",
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await log_channel.send(embed=log_embed, file=file)

        # 3. Эмбед для ЛС пользователя (Как на скриншоте)
        user_embed = discord.Embed(
            description=f"## <:emoji_name:1463153492595310644> Закрытый тикет",
            color=Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )
        user_embed.add_field(name="Название тикета", value=f"`{self.ticket_channel.name}`", inline=True)
        user_embed.add_field(name="Кто закрыл", value=interaction.user.mention, inline=True)
        user_embed.add_field(name="Участники", value=participants_text, inline=True)
        
        # Ставим аватар модератора
        user_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        user_embed.set_footer(text=f" {interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        try:
            view = PostTicketActions(html_data, self.ticket_channel.name, interaction.user.id)
            await self.opener.send(embed=user_embed, view=view)
        except: pass

        await interaction.followup.send("Канал удаляется...")
        await asyncio.sleep(5)
        await self.ticket_channel.delete()

    @discord.ui.button(label="Закрыть с причиной", style=ButtonStyle.grey)
    async def close_with_reason(self, interaction: Interaction, button: Button):
        if not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_channels):
            return await interaction.response.send_message("Только поддержка может это делать.", ephemeral=True)
        await interaction.response.send_modal(CloseReasonModal(self.ticket_channel, interaction.user))


class CloseReasonModal(Modal, title="Укажите причину закрытия"):
    reason = TextInput(label="Причина закрытия", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, ticket_channel: TextChannel, closer: discord.Member):
        super().__init__()
        self.ticket_channel = ticket_channel
        self.closer = closer

    async def on_submit(self, interaction: Interaction):
        reason_text = self.reason.value.strip()
        await interaction.response.defer(ephemeral=True)

        html_data = await generate_html_transcript(self.ticket_channel)
        
        stats = {}
        async for msg in self.ticket_channel.history(limit=None):
            if not msg.author.bot:
                stats[msg.author.display_name] = stats.get(msg.author.display_name, 0) + 1
        participants_text = "\n".join([f"{n} - {c} сообщений" for n, c in stats.items()]) or "Нет сообщений"

        # Архив
        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            file = discord.File(io.BytesIO(html_data.encode('utf-8')), filename=f"archive-{self.ticket_channel.name}.html")
            log_embed = discord.Embed(
                title="🗄️ Архив тикета",
                description=f"**Канал:** `{self.ticket_channel.name}`\n**Закрыл:** {interaction.user.mention}\n**Причина:** {reason_text}",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await log_channel.send(embed=log_embed, file=file)

        # Поиск автора тикета
        opener = None
        try:
            user_id = int(self.ticket_channel.topic.split("user_id=")[1].split("|")[0])
            opener = interaction.guild.get_member(user_id)
        except: pass

        if opener:
            user_embed = discord.Embed(
                description=f"## <:emoji_name:1463153492595310644> Ticket Closed", 
                color=Color.orange(), 
                timestamp=datetime.now(timezone.utc)
            )
            user_embed.add_field(name="Ticket Name", value=f"`{self.ticket_channel.name}`", inline=True)
            user_embed.add_field(name="Ticket Closed", value=self.closer.mention, inline=True)
            user_embed.add_field(name="Participants", value=participants_text, inline=True)
            user_embed.add_field(name="Reason", value=f"```\n{reason_text}\n```", inline=False)
            
            # Аватар модератора
            user_embed.set_thumbnail(url=self.closer.display_avatar.url)
            user_embed.set_footer(text=f"(*) {interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            view = PostTicketActions(html_data, self.ticket_channel.name, self.closer.id)
            try: await opener.send(embed=user_embed, view=view)
            except: pass

        await interaction.followup.send(f"Тикет закрыт.")
        await asyncio.sleep(5)
        await self.ticket_channel.delete()

class PostTicketActions(View):
    def __init__(self, transcript_html: str, ticket_name: str, moderator_id: int):
        super().__init__(timeout=None)
        self.transcript_html = transcript_html
        self.ticket_name = ticket_name
        self.moderator_id = moderator_id

    @discord.ui.button(label="Транскрипция", style=ButtonStyle.grey, emoji="📑")
    async def download_transcript(self, interaction: Interaction, button: Button):
        # Превращаем сохраненную строку HTML в файл прямо "на лету"
        file = discord.File(
            io.BytesIO(self.transcript_html.encode('utf-8')), 
            filename=f"transcript-{self.ticket_name}.html"
        )
        await interaction.response.send_message("Вот ваша полная история переписки:", file=file, ephemeral=True)

    @discord.ui.button(label="Оцените модератора", style=ButtonStyle.grey, emoji="⭐")
    async def rate_service(self, interaction: Interaction, button: Button):
        rate_view = View()
        for i in range(1, 6):
            btn = Button(label=f"{i} ⭐", style=ButtonStyle.blurple)
            
            # Функция-обработчик для каждой кнопки со звездой
            async def create_callback(rating):
                # Внутри callback кнопки оценки:
                async def callback(inter: Interaction):
                    mod_id_str = str(self.moderator_id) # JSON ключи всегда строки
                    if mod_id_str not in SUPPORT_STATS:
                        SUPPORT_STATS[mod_id_str] = []
                    
                    SUPPORT_STATS[mod_id_str].append(rating)
                    save_stats(SUPPORT_STATS) # Сохраняем в файл сразу
                    
                    await inter.response.send_message(f"Оценка {rating}⭐ сохранена!", ephemeral=True)
                return callback

            btn.callback = await create_callback(i)
            rate_view.add_item(btn)
            
        await interaction.response.send_message("Пожалуйста, оцените работу нашего специалиста:", view=rate_view, ephemeral=True)

async def generate_html_transcript(channel: TextChannel):
    messages = []
    # limit=None соберет вообще всю историю канала
    async for msg in channel.history(limit=None, oldest_first=True):
        time_str = msg.created_at.strftime('%Y-%m-%d %H:%M')
        # Обработка контента (текст или уведомление о вложении)
        content = msg.content if msg.content else "[Вложение или системное сообщение]"
        
        messages.append(f"""
        <div style="margin-bottom: 12px; padding: 8px; border-bottom: 1px solid #4f545c;">
            <b style="color: #5865F2; font-size: 1.1em;">{msg.author.display_name}</b> 
            <i style="color: #72767d; font-size: 0.85em; margin-left: 10px;">{time_str}</i><br>
            <div style="color: #dcddde; margin-top: 5px; line-height: 1.4;">{content}</div>
        </div>
        """)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Транскрипция - {channel.name}</title>
        <style>
            body {{ background-color: #36393f; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 30px; }}
            .container {{ max-width: 800px; margin: auto; background: #2f3136; padding: 20px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }}
            h2 {{ color: #ffffff; text-align: center; border-bottom: 2px solid #5865F2; padding-bottom: 15px; }}
            .footer {{ color: #72767d; text-align: center; margin-top: 20px; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Транскрипция: {channel.name}</h2>
            {"".join(messages)}
            <div class="footer">Создано системой поддержки Shiwo • {datetime.now().strftime('%Y-%m-%d')}</div>
        </div>
    </body>
    </html>
    """
    return html_content
class TicketSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Выберите тип запроса",
        custom_id="ticket_select_menu",
        options=[
            SelectOption(label="Подержка", description="У вас есть какие-то вопросы?", emoji="✉️"),
            SelectOption(label="Покупка", description="Запрос на покупку подписки.", emoji="🛒"),
            SelectOption(label="Партнёрство", description="Запрос на портнёрство.", emoji="🤝"),
            SelectOption(label="Черный список", description="Запрос на занесение в черный список.", emoji="🚫"),
        ]
    )
    async def select_callback(self, interaction: Interaction, select: Select):
    
        choice = select.values[0]
        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
          
            channel_names = {
                "Подержка": "support",
                "Покупка": "purchase",
                "Партнёрство": "partnership",
                "Черный список": "blacklist",
            }
            prefix = channel_names.get(choice, "ticket")

            
            guild = interaction.guild
            category = guild.get_channel(TICKET_CATEGORY_ID)
            
            if not category or not isinstance(category, discord.CategoryChannel):
                print(f"[ОШИБКА] Категория {TICKET_CATEGORY_ID} не найдена или это не категория.")
                return await interaction.followup.send("Ошибка конфигурации: категория тикетов не найдена.", ephemeral=True)

            
            if not guild.me.guild_permissions.manage_channels:
                return await interaction.followup.send("У бота недостаточно прав для создания каналов.", ephemeral=True)

            
            existing_ticket = None
            for channel in category.text_channels:
                if channel.topic and f"user_id={interaction.user.id}" in channel.topic and f"type={choice}" in channel.topic:
                    existing_ticket = channel
                    break

            if existing_ticket:
                return await interaction.followup.send(
                    f"У вас уже открыт тикет типа **{choice}**: {existing_ticket.mention}",
                    ephemeral=True
                )

            
            overwrites = {
                guild.default_role: PermissionOverwrite(view_channel=False),
                interaction.user: PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, read_message_history=True),
                guild.get_role(SUPPORT_ROLE_ID): PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                guild.me: PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
            }

           
            ticket_channel = await category.create_text_channel(
                name=f"{prefix}-{interaction.user.name.lower()}",
                topic=f"type={choice}|user_id={interaction.user.id}",
                overwrites=overwrites
            )

            
            opened_at = int(time.time())
            ticket_embed = discord.Embed(
                title="Тикет поддержки открыт",
                description=(
                    f"Привет {interaction.user.mention}, спасибо что связались с **Поддержкой Shiwo**!\n\n"
                    f"**Открыт:** <t:{opened_at}:R>\n\n"
                    "Пожалуйста, опишите вашу проблему подробно. Наша команда ответит вам в ближайшее время.\n\n"
                    "**Совет:** Прикрепите скриншоты или логи ошибок."
                ),
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            ticket_embed.set_author(name=f"Тикет: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
            ticket_embed.set_footer(text="Shiwo Support System")

            
            close_view = TicketCloseView(ticket_channel, interaction.user)
            await ticket_channel.send(
                content=f"{interaction.user.mention} | <@&{SUPPORT_ROLE_ID}>",
                embed=ticket_embed,
                view=close_view
            )

            
            log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="Новый тикет открыт",
                    description=f"**Тип:** {choice}\n**Пользователь:** {interaction.user.mention}\n**Канал:** {ticket_channel.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                await log_channel.send(embed=log_embed)

           
            confirm_embed = discord.Embed(
                title="Тикет создан!",
                description=f"Ваш тикет был успешно создан: {ticket_channel.mention}",
                color=discord.Color.from_rgb(54, 57, 63)
            )
            await interaction.followup.send(embed=confirm_embed, ephemeral=True)

            
            await interaction.message.edit(view=TicketSelectView())

        except Exception as e:
            print(f"[КРИТИЧЕСКАЯ ОШИБКА ТИКЕТОВ]: {e}")
            import traceback
            traceback.print_exc() 
            await interaction.followup.send("Произошла внутренняя ошибка при создании тикета.", ephemeral=True)


class AdminPanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup_admin")
    @commands.has_permissions(administrator=True)
    async def setup_admin_panel(self, ctx):
        """Создает сообщение-панель, которое можно обновлять"""
        embed = discord.Embed(
            title="🛡️ Панель управления персоналом",
            description="Используйте меню ниже, чтобы проверить эффективность саппортов.",
            color=discord.Color.gold()
        )
        # Класс AdminStatsView мы писали выше
        await ctx.send(embed=embed, view=AdminStatsView(ctx.guild))

# Обновляем AdminStatsView для работы с JSON
class AdminStatsView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)
        # Смени пароль здесь!
        self.admin_password = "cartel" 

    @discord.ui.button(label="Вся статистика", style=discord.ButtonStyle.green, custom_id="stats_all", emoji="<:stats:1463129091451650069>")
    async def show_all_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = load_stats()
        if not stats:
            return await interaction.response.send_message("Статистика пуста.", ephemeral=True)
        
        embed = discord.Embed(title="Общий отчет по команде", color=discord.Color.blue())
        for mod_id_str, ratings in stats.items():
            member = interaction.guild.get_member(int(mod_id_str))
            name = member.display_name if member else f"ID: {mod_id_str}"
            avg = sum(ratings) / len(ratings)
            embed.add_field(name=name, value=f"Рейтинг: **{avg:.2f}** ⭐ | Тикетов: **{len(ratings)}**", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="По модераторам", style=discord.ButtonStyle.blurple, custom_id="stats_by_mod", emoji="<:stats:1464710641817223410>")
    async def show_mod_select(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = load_stats()
        if not stats:
            return await interaction.response.send_message("Статистика пуста.", ephemeral=True)

        view = discord.ui.View(timeout=60)
        options = []
        for mod_id_str in stats.keys():
            member = interaction.guild.get_member(int(mod_id_str))
            if member:
                options.append(discord.SelectOption(label=member.display_name, value=mod_id_str))

        if not options:
            return await interaction.response.send_message("Активные модераторы не найдены в кэше сервера.", ephemeral=True)

        select = discord.ui.Select(placeholder="Выберите сотрудника для проверки...", options=options)

        async def select_callback(inter: discord.Interaction):
            mod_id = select.values[0]
            m_ratings = stats.get(mod_id, [])
            m_member = inter.guild.get_member(int(mod_id))
            
            avg = sum(m_ratings) / len(m_ratings) if m_ratings else 0
            
            # Эмбед с фото модератора
            e = discord.Embed(
                title=f"Профиль модератора: {m_member.display_name}", 
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            # Картинка модератора
            e.set_thumbnail(url=m_member.display_avatar.url)
            
            e.add_field(name="Общий рейтинг", value=f"**{avg:.2f} / 5.0** ⭐", inline=True)
            e.add_field(name="Закрыто тикетов", value=f"**{len(m_ratings)}**", inline=True)
            e.set_footer(text=f"ID: {mod_id}")
            
            await inter.response.send_message(embed=e, ephemeral=True)

        select.callback = select_callback
        view.add_item(select)
        await interaction.response.send_message("Выберите модератора из списка:", view=view, ephemeral=True)

    @discord.ui.button(label="Экспорт БД", style=discord.ButtonStyle.secondary, custom_id="stats_export", emoji="📥")
    async def export_database(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Доступ запрещен.", ephemeral=True)
            
        if not os.path.exists(STATS_FILE):
            return await interaction.response.send_message("Файл базы не найден.", ephemeral=True)

        file = discord.File(STATS_FILE, filename=f"backup_stats_{datetime.now().date()}.json")
        await interaction.response.send_message("Копия базы данных подготовлена:", file=file, ephemeral=True)

    @discord.ui.button(label="Сброс БД", style=discord.ButtonStyle.danger, custom_id="stats_reset_secure", emoji="<:error:1463122517102297214>")
    async def secure_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Только гл. администратор может сбросить базу.", ephemeral=True)
        await interaction.response.send_modal(ResetPasswordModal(self.admin_password))

class ResetPasswordModal(discord.ui.Modal, title="Подтверждение сброса базы"):
    password_input = discord.ui.TextInput(
        label="Введите пароль администратора",
        placeholder="Пароль...",
        required=True,
        min_length=4
    )

    def __init__(self, correct_password):
        super().__init__()
        self.correct_password = correct_password

    async def on_submit(self, interaction: discord.Interaction):
        if self.password_input.value == self.correct_password:
            # Очистка базы
            save_stats({}) 
            await interaction.response.send_message("База данных успешно очищена после проверки пароля.", ephemeral=True)
        else:
            await interaction.response.send_message("Неверный пароль! Доступ заблокирован.", ephemeral=True)

class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Регистрируем вьюшки БЕЗ аргументов
        self.bot.add_view(TicketSelectView())
        self.bot.add_view(AdminStatsView()) 

    async def setup_ticket_panel(self):
        # Поиск канала тикетов
        channel = self.bot.get_channel(TICKET_CHANNEL_ID) or await self.bot.fetch_channel(TICKET_CHANNEL_ID)
        if not channel:
            print(f"[ОШИБКА] Канал тикетов {TICKET_CHANNEL_ID} не найден!")
            return

        try:
            await channel.purge(limit=50)
            embed = discord.Embed(
                description=(
                    f"## <:emoji_name:1463153492595310644> | Shiwo Support\n"
                    f"**Создайте тикет**\n"
                    f"**Нужна помощь?** Выберите категорию."
                ),
                color=discord.Color.from_rgb(54, 57, 63)
            )
            embed.add_field(
                name="<:emoji_name:1463153494373437520> Прежде чем создавать тикет:",
                value="• Проверьте нашу документацию\n• Поищите существующие решения",
                inline=False
            )
            embed.set_image(url="https://media.discordapp.net/attachments/1462165491278938204/1463154984437809237/24237F17-FFC4-4390-8699-7A00C5798E47.png")
            
            await channel.send(embed=embed, view=TicketSelectView())
            print(f"[УСПЕХ] Панель тикетов отправлена в {channel.name}")
        except Exception as e:
            print(f"[ОШИБКА] setup_ticket_panel: {e}")

    async def setup_admin_stats_panel(self):
        channel = self.bot.get_channel(ADMIN_PANEL_CHANNEL_ID) or await self.bot.fetch_channel(ADMIN_PANEL_CHANNEL_ID)
        if not channel: return

        try:
            await channel.purge(limit=10)
            embed = discord.Embed(
                title="<:sheld:1464708871703761061> Админ-Панель Поддержки",
                description=(
                    "Ниже представлены инструменты для контроля работы модераторов.\n\n"
                    "<:sheld:1463129091451650069> **Вся статистика**: Общий рейтинг.\n"
                    "<:sheld:1464710641817223410> **По модераторам**: Личный отчет.\n"
                    "Возможность удалить базу данных и скачать её"
                ),
                color=discord.Color.from_rgb(54, 57, 63)
            )
            await channel.send(embed=embed, view=AdminStatsView())
            print("[УСПЕХ] Админ-панель отправлена.")
        except Exception as e:
            print(f"[ОШИБКА] setup_admin_stats_panel: {e}")


async def setup(bot):
    cog = TicketsCog(bot)
    await bot.add_cog(cog)