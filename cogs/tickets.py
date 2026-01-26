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
    Color, 
    PartialEmoji
)
from datetime import datetime, timezone
import asyncio
from math import ceil


from config import (
    TICKET_CHANNEL_ID,
    TICKET_CATEGORY_ID,
    TICKET_LOG_CHANNEL_ID,
    SUPPORT_ROLE_ID, 
    ADMIN_PANEL_CHANNEL_ID
)


DB_FILE = "transcripts.db"
ITEMS_PER_PAGE = 10  
ITEMS_PER_RATINGS_PAGE = 8  



def init_db():
   
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            moderator_id INTEGER NOT NULL,
            transcript TEXT NOT NULL,
            ticket_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS moderator_stats (
            moderator_id INTEGER PRIMARY KEY,
            total_tickets INTEGER DEFAULT 0,
            avg_rating REAL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_moderator_id ON ratings(moderator_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_ticket_moderator ON transcripts(moderator_id)')
    
    conn.commit()
    conn.close()



def save_transcript_data(moderator_id: int, transcript_html: str, ticket_name: str):
    
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
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT transcript, ticket_name FROM transcripts WHERE id = ?', (transcript_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {"transcript": row[0], "ticket_name": row[1]}
    return None


def delete_transcript_data(transcript_id: int):
   
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transcripts WHERE id = ?', (transcript_id,))
    conn.commit()
    conn.close()


def get_moderator_transcripts(moderator_id: int):
   
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



def save_rating(moderator_id: int, user_id: int, rating: int, transcript_id: int, ticket_name: str):
   
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO ratings (moderator_id, user_id, rating, transcript_id, ticket_name)
        VALUES (?, ?, ?, ?, ?)
    ''', (moderator_id, user_id, rating, transcript_id, ticket_name))
    
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


def get_all_moderator_stats(page: int = 1, limit: int = ITEMS_PER_PAGE):
   
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM moderator_stats')
    total_count = cursor.fetchone()[0]
    
    offset = (page - 1) * limit
    
    cursor.execute('''
        SELECT moderator_id, total_tickets, avg_rating FROM moderator_stats 
        ORDER BY avg_rating DESC
        LIMIT ? OFFSET ?
    ''', (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    
    total_pages = ceil(total_count / limit) if total_count > 0 else 1
    
    return {
        "data": {str(row[0]): {"total_tickets": row[1], "avg_rating": row[2]} for row in rows},
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page
    }


def get_moderator_ratings(moderator_id: int, page: int = 1, limit: int = ITEMS_PER_RATINGS_PAGE):
   
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM ratings WHERE moderator_id = ?', (moderator_id,))
    total_count = cursor.fetchone()[0]
    
    offset = (page - 1) * limit
    
    cursor.execute('''
        SELECT rating, ticket_name, rated_at, id FROM ratings 
        WHERE moderator_id = ? 
        ORDER BY rated_at DESC
        LIMIT ? OFFSET ?
    ''', (moderator_id, limit, offset))
    rows = cursor.fetchall()
    conn.close()
    
    total_pages = ceil(total_count / limit) if total_count > 0 else 1
    
    return {
        "data": rows,
        "total_count": total_count,
        "total_pages": total_pages,
        "current_page": page
    }




class AllStatsNavigationView(View):
    
    def __init__(self, page: int, total_pages: int, guild: discord.Guild):
        super().__init__(timeout=300)
        self.page = page
        self.total_pages = total_pages
        self.guild = guild
        
        if page <= 1:
            self.prev_page.disabled = True
        if page >= total_pages:
            self.next_page.disabled = True


    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey, custom_id="stats_prev")
    async def prev_page(self, interaction: Interaction, button: Button):
        if self.page > 1:
            await self.show_page(interaction, self.page - 1)


    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey, custom_id="stats_next")
    async def next_page(self, interaction: Interaction, button: Button):
        if self.page < self.total_pages:
            await self.show_page(interaction, self.page + 1)


    @discord.ui.button(label=f"Страница 1/1", style=discord.ButtonStyle.grey, custom_id="stats_page", disabled=True)
    async def page_button(self, interaction: Interaction, button: Button):
        pass


    async def show_page(self, interaction: Interaction, page: int):
        stats_result = get_all_moderator_stats(page=page, limit=ITEMS_PER_PAGE)
        stats = stats_result["data"]
        
        embed = discord.Embed(
            title="<:stats:1463129091451650069> Общий отчет по команде",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if not stats:
            embed.description = "Нет данных для отображения"
        else:
            for mod_id_str, data in stats.items():
                member = self.guild.get_member(int(mod_id_str))
                name = member.display_name if member else f"ID: {mod_id_str}"
                avg = data["avg_rating"]
                total = data["total_tickets"]
                embed.add_field(
                    name=f"<:name:1464710641817223410> {name}",
                    value=f"Рейтинг: **{avg:.2f}** <:star:1465302165756186634> | Тикетов: **{total}**",
                    inline=False
                )
        
        new_view = AllStatsNavigationView(page, stats_result["total_pages"], self.guild)
        new_view.page_button.label = f"Страница {page}/{stats_result['total_pages']}"
        
        embed.set_footer(
            text=f"Всего модераторов: {stats_result['total_count']} | Страница {page}/{stats_result['total_pages']}"
        )
        
        await interaction.response.edit_message(embed=embed, view=new_view)


class ModeratorSelectView(View):
    
    def __init__(self, guild: discord.Guild, page: int = 1, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.guild = guild
        self.page = page
        self.stats_result = get_all_moderator_stats(page=page, limit=ITEMS_PER_PAGE)
        self.total_pages = self.stats_result["total_pages"]
        
        self.populate_select()
        self.update_navigation_buttons()


    def populate_select(self):
        
        for item in self.children[:]:
            if isinstance(item, Select):
                self.remove_item(item)
        
        stats = self.stats_result["data"]
        options = []
        
        for mod_id_str in stats.keys():
            member = self.guild.get_member(int(mod_id_str))
            if member:
                data = stats[mod_id_str]
                label = f"{member.display_name} ({data['avg_rating']:.2f})"
                options.append(
                    discord.SelectOption(
                        label=label[:100],  
                        value=mod_id_str,
                        description=f"Тикетов: {data['total_tickets']}"
                    )
                )
        
        if options:
            select = discord.ui.Select(
                placeholder="Выберите сотрудника...",
                options=options,
                custom_id="mod_select_paginated"
            )
            select.callback = self.select_callback
            self.add_item(select)


    def update_navigation_buttons(self):
      
        for item in self.children[:]:
            if isinstance(item, Button):
                self.remove_item(item)
        
       
        prev_btn = discord.ui.Button(label="◀", style=discord.ButtonStyle.grey)
        prev_btn.callback = self.prev_page
        prev_btn.disabled = self.page <= 1
        self.add_item(prev_btn)
        
        
        page_info = discord.ui.Button(
            label=f"Страница {self.page}/{self.total_pages}",
            style=discord.ButtonStyle.grey,
            disabled=True
        )
        self.add_item(page_info)
        
        
        next_btn = discord.ui.Button(label="▶", style=discord.ButtonStyle.grey)
        next_btn.callback = self.next_page
        next_btn.disabled = self.page >= self.total_pages
        self.add_item(next_btn)


    async def prev_page(self, interaction: Interaction):
        if self.page > 1:
            self.page -= 1
            self.stats_result = get_all_moderator_stats(page=self.page, limit=ITEMS_PER_PAGE)
            self.populate_select()
            self.update_navigation_buttons()
            await interaction.response.edit_message(view=self)


    async def next_page(self, interaction: Interaction):
        if self.page < self.total_pages:
            self.page += 1
            self.stats_result = get_all_moderator_stats(page=self.page, limit=ITEMS_PER_PAGE)
            self.populate_select()
            self.update_navigation_buttons()
            await interaction.response.edit_message(view=self)


    async def select_callback(self, interaction: Interaction):
        mod_id = int(self.children[0].values[0])  
        await self.show_moderator_details(interaction, mod_id)


    async def show_moderator_details(self, interaction: Interaction, mod_id: int):
        stats_data = get_moderator_stats(mod_id)
        ratings_result = get_moderator_ratings(mod_id, page=1, limit=ITEMS_PER_RATINGS_PAGE)
        m_member = self.guild.get_member(mod_id)
        
        if not m_member:
            await interaction.response.send_message("Модератор не найден", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Профиль модератора: {m_member.display_name}",
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=m_member.display_avatar.url)
        embed.add_field(
            name="Общий рейтинг",
            value=f"**{stats_data['avg_rating']:.2f} / 5.0** <:star:1465302165756186634>",
            inline=True
        )
        embed.add_field(
            name="Закрыто тикетов",
            value=f"**{stats_data['total_tickets']}**",
            inline=True
        )
        
        if ratings_result["data"]:
            rating_text = "\n".join([
                f"**{r[1]}** - {r[0]}<:star:1465302165756186634>"
                for r in ratings_result["data"][:ITEMS_PER_RATINGS_PAGE]
            ])
            embed.add_field(name="Последние оценки", value=rating_text, inline=False)
        
        embed.set_footer(
            text=f"ID: {mod_id} | Страница 1/{ratings_result['total_pages']}"
        )
        
        view = RatingsNavigationView(mod_id, 1, ratings_result["total_pages"], self.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RatingsNavigationView(View):
   
    def __init__(self, moderator_id: int, page: int, total_pages: int, guild: discord.Guild):
        super().__init__(timeout=300)
        self.moderator_id = moderator_id
        self.page = page
        self.total_pages = total_pages
        self.guild = guild
        
        if page <= 1:
            self.prev_btn.disabled = True
        if page >= total_pages:
            self.next_btn.disabled = True


    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey, custom_id="ratings_prev")
    async def prev_btn(self, interaction: Interaction, button: Button):
        if self.page > 1:
            await self.show_page(interaction, self.page - 1)


    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey, custom_id="ratings_next")
    async def next_btn(self, interaction: Interaction, button: Button):
        if self.page < self.total_pages:
            await self.show_page(interaction, self.page + 1)


    @discord.ui.button(label=f"Страница 1/1", style=discord.ButtonStyle.grey, custom_id="ratings_page", disabled=True)
    async def page_btn(self, interaction: Interaction, button: Button):
        pass


    async def show_page(self, interaction: Interaction, page: int):
        ratings_result = get_moderator_ratings(self.moderator_id, page=page)
        stats_data = get_moderator_stats(self.moderator_id)
        m_member = self.guild.get_member(self.moderator_id)
        
        embed = discord.Embed(
            title=f"Профиль модератора: {m_member.display_name}",
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_thumbnail(url=m_member.display_avatar.url)
        embed.add_field(
            name="Общий рейтинг",
            value=f"**{stats_data['avg_rating']:.2f} / 5.0** <:star:1465302165756186634>",
            inline=True
        )
        embed.add_field(
            name="Закрыто тикетов",
            value=f"**{stats_data['total_tickets']}**",
            inline=True
        )
        
        if ratings_result["data"]:
            rating_text = "\n".join([
                f"**{r[1]}** - {r[0]}<:star:1465302165756186634>"
                for r in ratings_result["data"]
            ])
            embed.add_field(name="Оценки", value=rating_text, inline=False)
        else:
            embed.add_field(name="Оценки", value="Нет оценок на этой странице", inline=False)
        
        embed.set_footer(
            text=f"ID: {self.moderator_id} | Страница {page}/{ratings_result['total_pages']}"
        )
        
        new_view = RatingsNavigationView(self.moderator_id, page, ratings_result["total_pages"], self.guild)
        new_view.page_btn.label = f"Страница {page}/{ratings_result['total_pages']}"
        
        await interaction.response.edit_message(embed=embed, view=new_view)



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


    @discord.ui.button(label="Оцените модератора", style=ButtonStyle.grey, emoji="<:star:1465302165756186634>")
    async def rate_service(self, interaction: Interaction, button: Button):
        rate_view = View()
        for i in range(1, 6):
            star = PartialEmoji.from_str("<:star:1465302165756186634>")
            btn = Button(label=f"{i}", emoji=star, style=ButtonStyle.blurple)
            
            async def create_callback(rating):
                async def callback(inter: Interaction):
                    save_rating(
                        self.moderator_id,
                        inter.user.id,
                        rating,
                        self.transcript_id,
                        self.ticket_name
                    )
                    
                    await inter.response.send_message(f"Спасибо за оценку {rating}<:star:1465302165756186634>!", ephemeral=True)
                
                return callback


            btn.callback = await create_callback(i)
            rate_view.add_item(btn)
            
        await interaction.response.send_message(
            "Пожалуйста, оцените работу нашего специалиста:",
            view=rate_view,
            ephemeral=True
        )



class AdminStatsView(discord.ui.View):
    def __init__(self, *args, **kwargs):
        super().__init__(timeout=None)
        self.admin_password = "cartel"


    @discord.ui.button(
        label="Вся статистика",
        style=discord.ButtonStyle.green,
        custom_id="stats_all",
        emoji="<:stats:1463129091451650069>"
    )
    async def show_all_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats_result = get_all_moderator_stats(page=1, limit=ITEMS_PER_PAGE)
        stats = stats_result["data"]
        
        if not stats:
            return await interaction.response.send_message("Статистика пуста.", ephemeral=True)
        
        embed = discord.Embed(
            title="<:stats:1463129091451650069> Общий отчет по команде",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        for mod_id_str, data in stats.items():
            member = interaction.guild.get_member(int(mod_id_str))
            name = member.display_name if member else f"ID: {mod_id_str}"
            avg = data["avg_rating"]
            total = data["total_tickets"]
            embed.add_field(
                name=f"<:name:1464710641817223410> {name}",
                value=f"Рейтинг: **{avg:.2f}** <:star:1465302165756186634> | Тикетов: **{total}**",
                inline=False
            )
        
        embed.set_footer(
            text=f"Всего модераторов: {stats_result['total_count']} | Страница 1/{stats_result['total_pages']}"
        )
        
        view = AllStatsNavigationView(1, stats_result["total_pages"], interaction.guild)
        view.page_button.label = f"Страница 1/{stats_result['total_pages']}"
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


    @discord.ui.button(
        label="По модераторам",
        style=discord.ButtonStyle.blurple,
        custom_id="stats_by_mod",
        emoji="<:stats:1464710641817223410>"
    )
    async def show_mod_select(self, interaction: discord.Interaction, button: discord.ui.Button):
        stats_result = get_all_moderator_stats(page=1, limit=ITEMS_PER_PAGE)
        
        if not stats_result["data"]:
            return await interaction.response.send_message("Активные модераторы не найдены.", ephemeral=True)
        
        view = ModeratorSelectView(interaction.guild, page=1)
        await interaction.response.send_message(
            f"Выберите модератора ({stats_result['total_count']} всего)",
            view=view,
            ephemeral=True
        )


    @discord.ui.button(
        label="Экспорт БД",
        style=discord.ButtonStyle.secondary,
        custom_id="stats_export",
        emoji="📥"
    )
    async def export_database(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Доступ запрещен.", ephemeral=True)
            
        if not os.path.exists(DB_FILE):
            return await interaction.response.send_message("Файл базы не найден.", ephemeral=True)

        file = discord.File(DB_FILE, filename=f"backup_db_{datetime.now().date()}.db")
        await interaction.response.send_message("Копия базы данных подготовлена:", file=file, ephemeral=True)


    @discord.ui.button(
        label="Сброс БД",
        style=discord.ButtonStyle.danger,
        custom_id="stats_reset_secure",
        emoji="<:error:1463122517102297214>"
    )
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



class TicketCloseView(View):
    def __init__(self, ticket_channel: TextChannel = None, opener: discord.Member = None):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.opener = opener

    def is_staff(self, member: discord.Member) -> bool:
        """Вспомогательная функция для проверки прав"""
        # Проверка на администратора
        if member.guild_permissions.administrator:
            return True
        # Проверка на наличие роли поддержки по ID
        return any(role.id == SUPPORT_ROLE_ID for role in member.roles)

    @discord.ui.button(label="Закрыть", style=ButtonStyle.red, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: Interaction, button: Button):
        # 1. Проверка прав (Админ или Саппорт)
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("У вас нет прав для закрытия тикета! Это может сделать только поддержка.", ephemeral=True)

        if not self.ticket_channel:
            self.ticket_channel = interaction.channel
        
        if not self.opener:
            try:
                user_id = int(self.ticket_channel.topic.split("user_id=")[1].split("|")[0])
                self.opener = interaction.guild.get_member(user_id)
            except:
                pass

        await interaction.response.defer()

        # --- Логика генерации транскрипта и логирования ---
        html_data = await generate_html_transcript(self.ticket_channel)
        
        stats = {}
        async for msg in self.ticket_channel.history(limit=None):
            if not msg.author.bot:
                stats[msg.author.display_name] = stats.get(msg.author.display_name, 0) + 1
        participants_text = "\n".join([f"{n} - {c} сообщений" for n, c in stats.items()]) or "Нет сообщений"

        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            file = discord.File(io.BytesIO(html_data.encode('utf-8')), filename=f"archive-{self.ticket_channel.name}.html")
            log_embed = discord.Embed(
                title="Архив тикета",
                description=f"**Канал:** `{self.ticket_channel.name}`\n**Закрыл:** {interaction.user.mention}\n**Причина:** Без указания",
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await log_channel.send(embed=log_embed, file=file)

        # Отправка уведомления пользователю
        if self.opener:
            user_embed = discord.Embed(
                description=f"## <:emoji_name:1463153492595310644> Закрытый тикет",
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            user_embed.add_field(name="Название тикета", value=f"`{self.ticket_channel.name}`", inline=True)
            user_embed.add_field(name="Кто закрыл", value=interaction.user.mention, inline=True)
            user_embed.add_field(name="Участники", value=participants_text, inline=True)
            user_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            try:
                transcript_id = save_transcript_data(interaction.user.id, html_data, self.ticket_channel.name)
                view = PostTicketActions(interaction.user.id, transcript_id, self.ticket_channel.name)
                await self.opener.send(embed=user_embed, view=view)
            except: 
                pass

        await interaction.followup.send("Тикет будет удален через 5 секунд.")
        await asyncio.sleep(5)
        await self.ticket_channel.delete()

    @discord.ui.button(label="Закрыть с причиной", style=ButtonStyle.grey, custom_id="close_with_reason_btn")
    async def close_with_reason(self, interaction: Interaction, button: Button):
        # Проверка прав (Админ или Саппорт)
        if not self.is_staff(interaction.user):
            return await interaction.response.send_message("Только поддержка может это делать.", ephemeral=True)
            
        if not self.ticket_channel:
            self.ticket_channel = interaction.channel
            
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

        log_channel = interaction.guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if log_channel:
            file = discord.File(io.BytesIO(html_data.encode('utf-8')), filename=f"archive-{self.ticket_channel.name}.html")
            log_embed = discord.Embed(
                title="Архив тикета",
                description=f"**Канал:** `{self.ticket_channel.name}`\n**Закрыл:** {interaction.user.mention}\n**Причина:** {reason_text}",
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await log_channel.send(embed=log_embed, file=file)

        opener = None
        try:
            user_id = int(self.ticket_channel.topic.split("user_id=")[1].split("|")[0])
            opener = interaction.guild.get_member(user_id)
        except: pass

        if opener:
            user_embed = discord.Embed(
                description=f"## <:emoji_name:1463153492595310644> Тикет закрыт", 
                color=discord.Color.from_rgb(54, 57, 63), 
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
            deleted = await channel.purge(limit=None)
            print(f"[DEBUG] Удалено сообщений: {len(deleted)}")
            
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
                value="• Проверьте нашу [документацию](https://shiwo-ac.com/au/privacy)\n• [Поищите существующие решения](https://discord.com/channels/1450568583930318930/1457114969765187767)",
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
                    "<:sheld:1463129091451650069> **Вся статистика**: Общий рейтинг с пагинацией.\n"
                    "<:sheld:1464710641817223410> **По модераторам**: Личный отчет с поиском.\n"
                    "<:export:1465301465080795190>**Экспорт БД**: Скачать базу данных.\n"
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
