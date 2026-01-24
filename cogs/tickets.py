import discord
import time
import io
import os
import sqlite3
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

DB_FILE = "transcripts.db"

# ============ DATABASE INIT ============
def init_db():
    """Создает таблицы если их нет"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Таблица транскриптов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moderator_id INTEGER NOT NULL,
            transcript TEXT NOT NULL,
            ticket_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица рейтингов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moderator_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            transcript_id INTEGER,
            ticket_name TEXT,
            rated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(transcript_id) REFERENCES transcripts(id)
        )
    ''')
    
    # Таблица статистики модераторов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moderator_stats (
            moderator_id INTEGER PRIMARY KEY,
            total_tickets INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# ============ TRANSCRIPT FUNCTIONS ============
def save_transcript_data(moderator_id: int, transcript_html: str, ticket_name: str):
    """Сохраняет транскрипт в БД, возвращает ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transcripts (moderator_id, transcript, ticket_name)
        VALUES (?, ?, ?)
    ''', (moderator_id, transcript_html, ticket_name))
    conn.commit()
    transcript_id = cursor.lastrowid
    conn.close()
    return transcript_id

def load_transcript_data(transcript_id: int):
    """Загружает транскрипт по ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT transcript, ticket_name FROM transcripts WHERE id = ?', (transcript_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"transcript": row[0], "ticket_name": row[1]}
    return None

def delete_transcript_data(transcript_id: int):
    """Удаляет транскрипт по ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transcripts WHERE id = ?', (transcript_id,))
    conn.commit()
    conn.close()

def get_moderator_transcripts(moderator_id: int):
    """Получить все транскрипты модератора"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, ticket_name, created_at FROM transcripts 
        WHERE moderator_id = ? 
        ORDER BY created_at DESC
    ''', (moderator_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ============ RATING FUNCTIONS ============
def save_rating(moderator_id: int, user_id: int, rating: int, transcript_id: int, ticket_name: str):
    """Сохраняет оценку и обновляет статистику"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Сохраняем оценку
    cursor.execute('''
        INSERT INTO ratings (moderator_id, user_id, rating, transcript_id, ticket_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (moderator_id, user_id, rating, transcript_id, ticket_name))
    
    # Обновляем статистику модератора
    cursor.execute('''
        SELECT COUNT(*), AVG(rating) FROM ratings WHERE moderator_id = ?
    ''', (moderator_id,))
    
    total, avg = cursor.fetchone()
    
    cursor.execute('''
        INSERT OR REPLACE INTO moderator_stats (moderator_id, total_tickets, avg_rating, last_updated)
        VALUES (?, ?, ?, ?)
    ''', (moderator_id, total, avg or 0, datetime.now(timezone.utc)))
    
    conn.commit()
    conn.close()

def get_moderator_stats(moderator_id: int):
    """Получить статистику модератора"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT total_tickets, avg_rating FROM moderator_stats WHERE moderator_id = ?
    ''', (moderator_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"total_tickets": row[0], "avg_rating": row[1]}
    return {"total_tickets": 0, "avg_rating": 0}

def get_all_moderator_stats():
    """Получить статистику всех модераторов"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT moderator_id, total_tickets, avg_rating FROM moderator_stats 
        ORDER BY avg_rating DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    return {str(row[0]): {"total_tickets": row[1], "avg_rating": row[2]} for row in rows}

def get_moderator_ratings(moderator_id: int):
    """Получить все оценки модератора с информацией о тикетах"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT rating, ticket_name, rated_at, id FROM ratings 
        WHERE moderator_id = ? 
        ORDER BY rated_at DESC
    ''', (moderator_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ============ VIEWS ============

class PostTicketActions(View):
    def __init__(self, moderator_id: int, transcript_id: int, ticket_name: str):
        super().__init__(timeout=None)
        self.moderator_id = moderator_id
        self.transcript_id = transcript_id
        self.ticket_name = ticket_name

    @discord.ui.button(label="Транскрипция", style=ButtonStyle.grey, emoji="📑")
    async def download_transcript(self, interaction: Interaction, button: Button):
        data = load_transcript_data(self.transcript_id)
        
        if not data:
            await interaction.response.send_message("Транскрипт больше не доступен.", ephemeral=True)
            return
        
        file = discord.File(
            io.BytesIO(data["transcript"].encode('utf-8')), 
            filename=f"transcript-{data['ticket_name']}.html"
        )
        await interaction.response.send_message("Вот ваша полная история переписки:", file=file, ephemeral=True)

    @discord.ui.button(label="Оцените модератора", style=ButtonStyle.grey, emoji="⭐")
    async def rate_service(self, interaction: Interaction, button: Button):
        rate_view = View()
        for i in range(1, 6):
            btn = Button(label=f"{i} ⭐", style=ButtonStyle.blurple)
            
            async def create_callback(rating):
                async def callback(inter: Interaction):
                    save_rating(
                        self.moderator_id,
                        inter.user.id,
                        rating,
                        self.transcript_id,
                        self.ticket_name
                    )
                    
                    await inter.response.send_message(f"Спасибо за оценку {rating}⭐!", ephemeral=True)
                
                return callback

            btn.callback = await create_callback(i)
            rate_view.add_item(btn)
            
        await interaction.response.send_message(
            "Пожалуйста, оцените работу нашего специалиста:",
            view=rate_view,
            ephemeral=True
        )


class TicketCloseView(View):
    def __init__(self, ticket_channel: TextChannel = None, opener: discord.Member = None):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.opener = opener

    @discord.ui.button(label="Закрыть", style=ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: Interaction, button: Button):
        # Получаем канал из контекста если нет в памяти
        if not self.ticket_channel:
            self.ticket_channel = interaction.channel
        if not self.opener:
            try:
                user_id = int(self.ticket_channel.topic.split("user_id=")[1].split("|")[0])
                self.opener = interaction.guild.get_member(user_id)
            except:
                pass

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

        # 3. Эмбед для ЛС пользователя
        user_embed = discord.Embed(
            description=f"## <:emoji_name:1463153492595310644> Закрытый тикет",
            color=Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )
        user_embed.add_field(name="Название тикета", value=f"`{self.ticket_channel.name}`", inline=True)
        user_embed.add_field(name="Кто закрыл", value=interaction.user.mention, inline=True)
        user_embed.add_field(name="Участники", value=participants_text, inline=True)
        user_embed.set_thumbnail(url=interaction.user.display_avatar.url)
        user_embed.set_footer(text=f" {interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)

        try:
            transcript_id = save_transcript_data(interaction.user.id, html_data, self.ticket_channel.name)
            view = PostTicketActions(interaction.user.id, transcript_id, self.ticket_channel.name)
            await self.opener.send(embed=user_embed, view=view)
        except: pass

        await interaction.followup.send("Канал удаляется...")
        await asyncio.sleep(5)
        await self.ticket_channel.delete()

    @discord.ui.button(label="Закрыть с причиной", style=ButtonStyle.grey, custom_id="close_with_reason_btn")
    async def close_with_reason(self, interaction: Interaction, button: Button):
        if not self.ticket_channel:
            self.ticket_channel = interaction.channel
            
        if not (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_channels):
            return await interaction.response.send_message("Только поддержка может это делать.", ephemeral=True)
        await interaction.response.send_modal(CloseReasonModal(self.ticket_channel, interaction.user))



class CloseReasonModal(Modal, title="Укажите причину закрытия"):
    reason = TextInput(label="Причина закрытия", style=discord.TextStyle.paragraph, required=True)

    def __init__(self, ticket_channel: TextChannel = None, closer: discord.Member = None):
        super().__init__()
        self.ticket_channel = ticket_channel
        self.closer = closer

    async def on_submit(self, interaction: Interaction):
        reason_text = self.reason.value.strip()
        await interaction.response.defer(ephemeral=True)

        # Получаем канал если нет в памяти
        if not self.ticket_channel:
            self.ticket_channel = interaction.channel
        if not self.closer:
            self.closer = interaction.user

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
                description=f"## <:emoji_name:1463153492595310644> Тикет закрыт", 
                color=Color.orange(), 
                timestamp=datetime.now(timezone.utc)
            )
            user_embed.add_field(name="Название тикета", value=f"`{self.ticket_channel.name}`", inline=True)
            user_embed.add_field(name="Закрыт", value=self.closer.mention, inline=True)
            user_embed.add_field(name="Участники", value=participants_text, inline=True)
            user_embed.add_field(name="Причина", value=f"```\n{reason_text}\n```", inline=False)
            user_embed.set_thumbnail(url=self.closer.display_avatar.url)
            user_embed.set_footer(text=f"{interaction.guild.name}", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            transcript_id = save_transcript_data(self.closer.id, html_data, self.ticket_channel.name)
            view = PostTicketActions(self.closer.id, transcript_id, self.ticket_channel.name)
            try: await opener.send(embed=user_embed, view=view)
            except: pass

        await interaction.followup.send(f"Тикет закрыт.")
        await asyncio.sleep(5)
        await self.ticket_channel.delete()



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


class AdminStatsView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)
        self.admin_password = "cartel"

    @discord.ui.button(label="Вся статистика", style=discord.ButtonStyle.green, custom_id="stats_all", emoji="<:stats:1463129091451650069>")
    async def show_all_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = get_all_moderator_stats()
        if not stats:
            return await interaction.response.send_message("Статистика пуста.", ephemeral=True)
        
        embed = discord.Embed(title="📊 Общий отчет по команде", color=discord.Color.blue())
        for mod_id_str, data in stats.items():
            member = interaction.guild.get_member(int(mod_id_str))
            name = member.display_name if member else f"ID: {mod_id_str}"
            avg = data["avg_rating"]
            total = data["total_tickets"]
            embed.add_field(
                name=name,
                value=f"Рейтинг: **{avg:.2f}** ⭐ | Тикетов: **{total}**",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="По модераторам", style=discord.ButtonStyle.blurple, custom_id="stats_by_mod", emoji="<:stats:1464710641817223410>")
    async def show_mod_select(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats = get_all_moderator_stats()
        if not stats:
            return await interaction.response.send_message("Статистика пуста.", ephemeral=True)

        view = discord.ui.View(timeout=60)
        options = []
        for mod_id_str in stats.keys():
            member = interaction.guild.get_member(int(mod_id_str))
            if member:
                options.append(discord.SelectOption(label=member.display_name, value=mod_id_str))

        if not options:
            return await interaction.response.send_message("Активные модераторы не найдены.", ephemeral=True)

        select = discord.ui.Select(placeholder="Выберите сотрудника...", options=options)

        async def select_callback(inter: discord.Interaction):
            mod_id = int(select.values[0])
            stats_data = get_moderator_stats(mod_id)
            ratings = get_moderator_ratings(mod_id)
            m_member = inter.guild.get_member(mod_id)
            
            e = discord.Embed(
                title=f"Профиль модератора: {m_member.display_name}", 
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            e.set_thumbnail(url=m_member.display_avatar.url)
            e.add_field(name="Общий рейтинг", value=f"**{stats_data['avg_rating']:.2f} / 5.0** ⭐", inline=True)
            e.add_field(name="Закрыто тикетов", value=f"**{stats_data['total_tickets']}**", inline=True)
            
            if ratings:
                rating_text = "\n".join([
                    f"**{r[1]}** - {r[0]}⭐ ({r[2].split()[0]})"
                    for r in ratings[:10]
                ])
                e.add_field(name="Последние оценки", value=rating_text, inline=False)
            
            e.set_footer(text=f"ID: {mod_id}")
            await inter.response.send_message(embed=e, ephemeral=True)

        select.callback = select_callback
        view.add_item(select)
        await interaction.response.send_message("Выберите модератора из списка:", view=view, ephemeral=True)

    @discord.ui.button(label="Экспорт БД", style=discord.ButtonStyle.secondary, custom_id="stats_export", emoji="📥")
    async def export_database(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Доступ запрещен.", ephemeral=True)
            
        if not os.path.exists(DB_FILE):
            return await interaction.response.send_message("Файл базы не найден.", ephemeral=True)

        file = discord.File(DB_FILE, filename=f"backup_db_{datetime.now().date()}.db")
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
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM ratings')
            cursor.execute('DELETE FROM moderator_stats')
            cursor.execute('DELETE FROM transcripts')
            conn.commit()
            conn.close()
            await interaction.response.send_message("База данных успешно очищена.", ephemeral=True)
        else:
            await interaction.response.send_message("Неверный пароль! Доступ заблокирован.", ephemeral=True)


async def generate_html_transcript(channel: TextChannel):
    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        time_str = msg.created_at.strftime('%Y-%m-%d %H:%M')
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


class TicketsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()
        self.bot.add_view(TicketSelectView())
        self.bot.add_view(TicketCloseView()) 
        self.bot.add_view(AdminStatsView())



    async def setup_ticket_panel(self):
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
                value="• Проверьте нашу [документацию](#)\n• Поищите существующие решения",
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
                    "📥 **Экспорт БД**: Скачать базу данных.\n"
                    "<:error:1463122517102297214> **Сброс БД**: Очистить данные."
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
