import discord
from discord.ext import commands, tasks
from discord.ui import Modal, TextInput, View, Button
from discord import Interaction, ButtonStyle, Color, Guild
from datetime import datetime, timezone
import random
import time
import math
import sqlite3
from pathlib import Path
from typing import Dict, Optional, List


from config import (
    GIVEAWAY_USER_CHANNEL_ID,
    GIVEAWAY_ADMIN_CHANNEL_ID,
    GIVEAWAY_LOG_CHANNEL_ID,
    MAX_WINNERS
)


DB_PATH = Path("giveaway.db")


def init_giveaway_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS giveaways (
            id TEXT PRIMARY KEY,
            description TEXT,
            prize TEXT,
            sponsor TEXT,
            winner_count INTEGER,
            end_time TEXT,
            status TEXT,
            fixed_message_id INTEGER,
            participants TEXT,
            winners TEXT,
            preselected_winners TEXT,
            preselected_by INTEGER,
            preselected_at TEXT,
            finished_at TEXT,
            guild_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def load_giveaway_data() -> Optional[Dict]:
    init_giveaway_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, description, prize, sponsor, winner_count, end_time, status,
               fixed_message_id, participants, winners, preselected_winners,
               preselected_by, preselected_at, finished_at, guild_id
        FROM giveaways
        ORDER BY created_at DESC
        LIMIT 1
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return {
        "id": row[0],
        "description": row[1],
        "prize": row[2],
        "sponsor": row[3],
        "winner_count": row[4],
        "end_time": row[5],
        "status": row[6],
        "fixed_message_id": row[7],
        "participants": eval(row[8]) if row[8] else [],
        "winners": eval(row[9]) if row[9] else [],
        "preselected_winners": eval(row[10]) if row[10] else [],
        "preselected_by": row[11],
        "preselected_at": row[12],
        "finished_at": row[13],
        "guild_id": row[14]
    }


def save_giveaway_data(data: Dict):
    init_giveaway_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    participants_str = str(data.get("participants", []))
    winners_str = str(data.get("winners", []))
    preselected_winners_str = str(data.get("preselected_winners", []))
    
    cursor.execute('''
        INSERT OR REPLACE INTO giveaways 
        (id, description, prize, sponsor, winner_count, end_time, status,
         fixed_message_id, participants, winners, preselected_winners,
         preselected_by, preselected_at, finished_at, guild_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("id"),
        data.get("description"),
        data.get("prize"),
        data.get("sponsor"),
        data.get("winner_count", 1),
        data.get("end_time"),
        data.get("status", "active"),
        data.get("fixed_message_id"),
        participants_str,
        winners_str,
        preselected_winners_str,
        data.get("preselected_by"),
        data.get("preselected_at"),
        data.get("finished_at"),
        data.get("guild_id")
    ))
    
    conn.commit()
    conn.close()


def get_all_giveaways() -> list:
    init_giveaway_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, description, prize, sponsor, winner_count, end_time, status,
               fixed_message_id, participants, winners, preselected_winners,
               preselected_by, preselected_at, finished_at, guild_id
        FROM giveaways
        ORDER BY created_at DESC
    ''')
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "description": row[1],
            "prize": row[2],
            "sponsor": row[3],
            "winner_count": row[4],
            "end_time": row[5],
            "status": row[6],
            "fixed_message_id": row[7],
            "participants": eval(row[8]) if row[8] else [],
            "winners": eval(row[9]) if row[9] else [],
            "preselected_winners": eval(row[10]) if row[10] else [],
            "preselected_by": row[11],
            "preselected_at": row[12],
            "finished_at": row[13],
            "guild_id": row[14]
        })
    
    return result


def delete_giveaway(giveaway_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM giveaways WHERE id = ?', (giveaway_id,))
    conn.commit()
    conn.close()


class GiveawayEditModal(Modal, title="Настройка розыгрыша"):
    description = TextInput(label="Описание", style=discord.TextStyle.long, placeholder="Что нужно сделать участникам?", required=True)
    prize = TextInput(label="Приз", placeholder="Например: VIP статус на месяц", required=True)
    sponsor = TextInput(label="Спонсор", placeholder="Кто предоставил приз?", required=True)
    winner_count = TextInput(label="Количество победителей", placeholder="Например: 3", default="1", required=True)
    end_time = TextInput(label="Время окончания", placeholder="YYYY-MM-DD HH:MM", required=True)

    async def on_submit(self, interaction: Interaction):
        try:
            w_count = int(self.winner_count.value)
            if w_count < 1 or w_count > MAX_WINNERS:
                raise ValueError
            
            end_dt = datetime.strptime(self.end_time.value, "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(f"Ошибка: Количество победителей должно быть числом от 1 до {MAX_WINNERS}, а дата в формате ГГГГ-ММ-ДД ЧЧ:ММ", ephemeral=True)
            return

        old_data = load_giveaway_data()
        temp_data = {
            "description": self.description.value,
            "prize": self.prize.value,
            "sponsor": self.sponsor.value,
            "winner_count": w_count,
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
            "participants": old_data.get("participants", []) if old_data else [],
            "status": "active",
            "guild_id": interaction.guild.id
        }
        
        preview_embed = discord.Embed(
            title="Предпросмотр розыгрыша",
            description=temp_data["description"],
            color=discord.Color.from_rgb(54, 57, 63)
        )
        preview_embed.add_field(name="<:present:1466443598055870730> Приз", value=temp_data["prize"], inline=True)
        preview_embed.add_field(name="<:present:1466443596356915394> Спонсор", value=temp_data["sponsor"], inline=True)
        preview_embed.add_field(name="<:present:1466443614002352240> Окончание", value=temp_data["end_time"], inline=False)
        preview_embed.add_field(name="<:present:1466443593861431548> Участников", value=str(len(temp_data["participants"])), inline=False)

        view = GiveawayPreviewView(temp_data)
        await interaction.response.send_message(embed=preview_embed, view=view, ephemeral=True)


class WinnerSelectModal(Modal, title="Выбор победителей"):
    winners = TextInput(
        label="ID победителей",
        placeholder="Введите ID через пробел или запятую...",
        style=discord.TextStyle.long,
        required=True,
        max_length=1500
    )

    async def on_submit(self, interaction: Interaction):
        data = load_giveaway_data()
        if not data or data.get("status") == "finished":
            await interaction.response.send_message("Нет активного розыгрыша", ephemeral=True)
            return

        target_count = data.get("winner_count", 1)
        input_text = self.winners.value.replace(",", " ").split()
        winner_ids = []
        
        for raw_id in input_text:
            try:
                winner_ids.append(int(raw_id.strip()))
            except ValueError:
                await interaction.response.send_message(f"Ошибка в формате ID: `{raw_id}`", ephemeral=True)
                return

        if len(winner_ids) != target_count:
            await interaction.response.send_message(
                f"В настройках розыгрыша указано **{target_count}** победителей.\n"
                f"Вы ввели **{len(winner_ids)}** ID. Пожалуйста, введите ровно столько, сколько заявлено.",
                ephemeral=True
            )
            return
        
        guild = interaction.guild
        mentions_list = []

        for wid in winner_ids:
            user = guild.get_member(wid)
            if user:
                mentions_list.append(user.mention)
            else:
                mentions_list.append(f"ID {wid} (не найден)")

        log_channel = guild.get_channel(GIVEAWAY_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="Победители назначены вручную",
                description=(
                    f"**Розыгрыш ID:** `{data.get('id', 'N/A')}`\n"
                    f"**Администратор:** {interaction.user.mention}\n"
                    f"**Выбранные победители:**\n{', '.join(mentions_list)}\n\n"
                    f"Результаты будут опубликованы: `{data.get('end_time')}`"
                ),
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=log_embed)

        data["preselected_winners"] = winner_ids
        data["preselected_by"] = interaction.user.id
        data["preselected_at"] = datetime.now(timezone.utc).isoformat()
        save_giveaway_data(data)

        await update_user_giveaway_embed(interaction.guild)

        await interaction.response.send_message(
            f"Успешно! Выбрано победителей: **{len(winner_ids)}**.\n"
            f"Они будут объявлены автоматически в назначенное время.",
            ephemeral=True
        )


class GiveawayPreviewView(View):
    def __init__(self, temp_data):
        super().__init__(timeout=300)
        self.temp_data = temp_data

    @discord.ui.button(label="Подтвердить", emoji="<:apr:1466443618683457577>", style=ButtonStyle.green)
    async def confirm(self, interaction: Interaction, button: Button):
        try:
            old_data = load_giveaway_data()
            new_data = self.temp_data.copy()
            
            if old_data and "fixed_message_id" in old_data:
                new_data["fixed_message_id"] = old_data["fixed_message_id"]

            new_data["status"] = "active"
            new_data["id"] = "giveaway_" + str(int(time.time()))
            new_data["participants"] = []
            new_data.pop("winners", None)
            new_data.pop("preselected_winners", None)
            new_data.pop("preselected_by", None)
            new_data.pop("preselected_at", None)

            save_giveaway_data(new_data)
            print(f"[РОЗЫГРЫШ] Данные нового розыгрыша {new_data['id']} сохранены.")

            log_channel = interaction.guild.get_channel(GIVEAWAY_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(
                    title="Создан новый розыгрыш",
                    description=(
                        f"**Описание:** {new_data['description']}\n"
                        f"**Приз:** {new_data['prize']}\n"
                        f"**Спонсор:** {new_data['sponsor']}\n"
                        f"**Кол-во победителей:** {new_data['winner_count']}\n"
                        f"**Окончание:** {new_data['end_time']}"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.now(timezone.utc)
                )
                log_embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
                await log_channel.send(embed=log_embed)

            await update_user_giveaway_embed(interaction.guild)

            embed = discord.Embed(
                description="Розыгрыш успешно обновлен!",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.stop()

        except Exception as e:
            print(f"[ОШИБКА] confirm: {e}")
            import traceback
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Ошибка: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Ошибка: {e}", ephemeral=True)

    @discord.ui.button(label="Отредактировать заново", emoji="<:edit:1466443592573648906>", style=ButtonStyle.grey)
    async def edit_again(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(GiveawayEditModal())
        self.stop()


class GiveawayParticipantsPagination(View):
    def __init__(self, participants: list, author_id: int):
        super().__init__(timeout=180)
        self.participants = participants
        self.author_id = author_id
        self.page = 0
        self.per_page = 25
        self.total_pages = max(1, math.ceil(len(self.participants) / self.per_page))
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.total_pages - 1

    def get_embed(self) -> discord.Embed:
        start = self.page * self.per_page
        end = start + self.per_page
        chunk = self.participants[start:end]
        
        lines = [f"{start + i + 1}. <@{uid}>" for i, uid in enumerate(chunk)]
        text = "\n".join(lines) if lines else "Нет участников"

        embed = discord.Embed(
            title="Список участников розыгрыша",
            description=text,
            color=discord.Color.from_rgb(54, 57, 63)
        )
        embed.set_footer(text=f"Страница {self.page + 1}/{self.total_pages} • Всего: {len(self.participants)}")
        return embed

    async def _check_user(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Это меню открыто не вами.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="◀", style=ButtonStyle.secondary, custom_id="giveaway_prev")
    async def prev_button(self, interaction: Interaction, button: Button):
        if not await self._check_user(interaction):
            return
        self.page -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="▶", style=ButtonStyle.secondary, custom_id="giveaway_next")
    async def next_button(self, interaction: Interaction, button: Button):
        if not await self._check_user(interaction):
            return
        self.page += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)


class GiveawayUserView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Участвовать", style=ButtonStyle.primary, custom_id="giveaway_join")
    async def join_giveaway(self, interaction: Interaction, button: Button):
        data = load_giveaway_data()
        if not data:
            await interaction.response.send_message("Нет активного розыгрыша.", ephemeral=True)
            return

        user_id = interaction.user.id
        if user_id in data["participants"]:
            await interaction.response.send_message("Вы уже участвуете в розыгрыше.", ephemeral=True)
            return

        data["participants"].append(user_id)
        save_giveaway_data(data)

        log_channel = interaction.guild.get_channel(GIVEAWAY_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="Новый участник розыгрыша",
                description=f"**Пользователь:** {interaction.user.mention} ({user_id})\n**Розыгрыш ID:** {data['id']}",
                color=Color.green()
            )
            await log_channel.send(embed=log_embed)

        await update_user_giveaway_embed(interaction.guild)
        await interaction.response.send_message("Вы успешно участвуете в розыгрыше!", ephemeral=True)

    @discord.ui.button(label="Просмотреть список участников", style=ButtonStyle.secondary, custom_id="giveaway_list")
    async def view_list(self, interaction: Interaction, button: Button):
        data = load_giveaway_data()
        if not data:
            await interaction.response.send_message("Нет активного розыгрыша.", ephemeral=True)
            return

        participants = data["participants"]
        if not participants:
            await interaction.response.send_message("Нет участников в розыгрыше.", ephemeral=True)
            return

        view = GiveawayParticipantsPagination(participants=participants, author_id=interaction.user.id)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)


class GiveawayAdminView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Редактировать розыгрыш", emoji="<:edit:1466443592573648906>", style=ButtonStyle.primary, custom_id="giveaway_edit")
    async def edit_giveaway(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Только администраторы.", ephemeral=True)
            return
        await interaction.response.send_modal(GiveawayEditModal())

    @discord.ui.button(label="Выбрать победителя", emoji="<:chz:1466443589843292386>", style=ButtonStyle.success, custom_id="giveaway_select_winner")
    async def select_winner(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Только администраторы.", ephemeral=True)
            return

        data = load_giveaway_data()
        if not data:
            await interaction.response.send_message("Нет активного розыгрыша.", ephemeral=True)
            return

        await interaction.response.send_modal(WinnerSelectModal())

    @discord.ui.button(label="Рандомный выбор", emoji="🎲", style=ButtonStyle.blurple, custom_id="giveaway_random_winner")
    async def random_winner(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Только администраторы.", ephemeral=True)
            return

        data = load_giveaway_data()
        if not data:
            await interaction.response.send_message("Нет активного розыгрыша.", ephemeral=True)
            return

        participants = data.get("participants", [])
        if not participants:
            await interaction.response.send_message("Нет участников в розыгрыше.", ephemeral=True)
            return

        target_count = data.get("winner_count", 1)
        actual_winners_count = min(len(participants), target_count)
        winner_ids = random.sample(participants, actual_winners_count)

        guild = interaction.guild
        mentions_list = []

        for wid in winner_ids:
            user = guild.get_member(wid)
            if user:
                mentions_list.append(user.mention)
            else:
                mentions_list.append(f"ID {wid} (не найден)")

        log_channel = guild.get_channel(GIVEAWAY_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="Победители выбраны случайно",
                description=(
                    f"**Розыгрыш ID:** `{data.get('id', 'N/A')}`\n"
                    f"**Администратор:** {interaction.user.mention}\n"
                    f"**Выбранные победители:**\n{', '.join(mentions_list)}\n\n"
                    f"Результаты будут опубликованы: `{data.get('end_time')}`"
                ),
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            await log_channel.send(embed=log_embed)

        data["preselected_winners"] = winner_ids
        data["preselected_by"] = interaction.user.id
        data["preselected_at"] = datetime.now(timezone.utc).isoformat()
        save_giveaway_data(data)

        await update_user_giveaway_embed(interaction.guild)

        await interaction.response.send_message(
            f"Случайно выбрано победителей: **{len(winner_ids)}**.\n"
            f"Они будут объявлены автоматически в назначенное время.",
            ephemeral=True
        )



async def update_user_giveaway_embed(guild: Guild):
    data = load_giveaway_data()
    channel = guild.get_channel(GIVEAWAY_USER_CHANNEL_ID)
    
    if not channel:
        print(f"[РОЗЫГРЫШ] Канал {GIVEAWAY_USER_CHANNEL_ID} не найден")
        return

    fixed_message_id = data.get("fixed_message_id") if data else None
    message = None
    
    if fixed_message_id:
        try: 
            message = await channel.fetch_message(fixed_message_id)
        except discord.NotFound:
            print(f"[РОЗЫГРЫШ] Сообщение {fixed_message_id} не найдено")
            fixed_message_id = None
            if data:
                data["fixed_message_id"] = None
                save_giveaway_data(data)
        except Exception as e:
            print(f"[РОЗЫГРЫШ] Ошибка при поиске сообщения: {e}")
            fixed_message_id = None

    if not message and data:
        try:
            async for msg in channel.history(limit=100):
                if msg.author == guild.me and msg.embeds:
                    if "РОЗЫГРЫШ" in msg.embeds[0].title or "ЗАВЕРШЕН" in msg.embeds[0].title:
                        message = msg
                        data["fixed_message_id"] = message.id
                        save_giveaway_data(data)
                        print(f"[РОЗЫГРЫШ] Найдено существующее сообщение (ID: {message.id})")
                        break
        except Exception as e:
            print(f"[РОЗЫГРЫШ] Ошибка при поиске в истории: {e}")

    if data and data.get("status") != "finished":
        try:
            end_timestamp = int(datetime.strptime(data['end_time'], '%Y-%m-%d %H:%M').timestamp())
        except Exception as e:
            print(f"[РОЗЫГРЫШ] Ошибка парсинга даты: {e}")
            end_timestamp = 0

        embed = discord.Embed(
            title="РОЗЫГРЫШ",
            description=f"```\n{data.get('description')}\n```",
            color=discord.Color.from_rgb(54, 57, 63) 
        )
        
        embed.add_field(name="<:present:1466443598055870730> Приз", value=f"**```{data.get('prize')}```**", inline=False)
        
        info_value = (
            f"<:emoji3:1466443596356915394> **Спонсор:** `{data.get('sponsor')}`\n"
            f"<:emoji4:1466443588274487533> **Победителей:** `{data.get('winner_count', 1)}`"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        
        embed.add_field(name="Статус", value=(
            f"<:emoji7:1466443593861431548> **Участников:** `{len(data.get('participants', []))}`\n"
            f"<:present:1466443614002352240> **Завершение:** <t:{end_timestamp}:R>"
        ), inline=True)
        
        embed.set_footer(text="Нажми на кнопку ниже, чтобы испытать удачу!")
        view = GiveawayUserView()

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

    else:
        embed = discord.Embed(
            title="РОЗЫГРЫШ ЗАВЕРШЕН",
            color=discord.Color.from_rgb(54, 57, 63)
        )
        embed.add_field(
            name="Был разыгран приз",
            value=f"**{data.get('prize', '---') if data else '---'}**",
            inline=False
        )
        
        if data and data.get("winners"):
            mentions = [f"<@{wid}>" for wid in data["winners"]]
            embed.add_field(
                name="<:emoji4:1466443588274487533> Победители",
                value="\n".join(mentions) if mentions else "Не определены",
                inline=False
            )
        else:
            embed.add_field(
                name="<:emoji4:1466443588274487533> Победители",
                value="Нет участников",
                inline=False
            )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(text="Следите за новыми анонсами!")
        view = None

    if message:
        try:
            await message.edit(embed=embed, view=view)
            print(f"[РОЗЫГРЫШ] Эмбед обновлен (ID: {message.id})")
        except discord.NotFound:
            print(f"[РОЗЫГРЫШ] Сообщение было удалено, создаю новое")
            message = None
        except Exception as e:
            print(f"[РОЗЫГРЫШ] Ошибка при редактировании: {e}")
            message = None
    
    if not message and data:
        try:
            message = await channel.send(embed=embed, view=view)
            data["fixed_message_id"] = message.id
            save_giveaway_data(data)
            print(f"[РОЗЫГРЫШ] Эмбед создан (ID: {message.id})")
        except Exception as e:
            print(f"[РОЗЫГРЫШ] Ошибка при создании сообщения: {e}")


class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_giveaway_db()
        self.check_giveaway_end.start()
        self.bot.add_view(GiveawayUserView())
        self.bot.add_view(GiveawayAdminView())

    def cog_unload(self):
        self.check_giveaway_end.cancel()

    async def setup_giveaway_panels(self, guild: Guild = None):
        if not guild:
            if not self.bot.guilds:
                print("[РОЗЫГРЫШ] Бот не находится ни на одном сервере.")
                return
            guild = self.bot.guilds[0]

        print(f"[РОЗЫГРЫШ] Инициализирую панели для сервера: {guild.name}")

        await update_user_giveaway_embed(guild)

        admin_channel = guild.get_channel(GIVEAWAY_ADMIN_CHANNEL_ID)
        if admin_channel:
            try:
                await admin_channel.purge(limit=50)
                print(f"[РОЗЫГРЫШ] Админский канал очищен")
            except Exception as e:
                print(f"[РОЗЫГРЫШ] Ошибка при очистке админского канала: {e}")

            try:
                admin_embed = discord.Embed(
                    title="Панель редактирования розыгрыша",
                    description="Используйте кнопки ниже для управления розыгрышем",
                    color=discord.Color.from_rgb(54, 57, 63)
                )
                view = GiveawayAdminView()
                await admin_channel.send(embed=admin_embed, view=view)
                print(f"[РОЗЫГРЫШ] Админ панель создана")
            except Exception as e:
                print(f"[РОЗЫГРЫШ] Ошибка при создании админ панели: {e}")
        else:
            print(f"[РОЗЫГРЫШ] Админский канал {GIVEAWAY_ADMIN_CHANNEL_ID} не найден")

    @tasks.loop(minutes=1)
    async def check_giveaway_end(self):
        try:
            data = load_giveaway_data()
            
            if not data or data.get("status") == "finished":
                return

            if not self.bot.guilds:
                return

            guild_id = data.get("guild_id")
            guild = None
            
            if guild_id:
                guild = self.bot.get_guild(guild_id)
            
            if not guild:
                guild = self.bot.guilds[0]
            
            end_time_str = data.get("end_time")
            if not end_time_str:
                return

            end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
            current_time = datetime.now()
            
            if current_time >= end_dt:
                print(f"[РОЗЫГРЫШ] Розыгрыш завершен!")
                
                participants = data.get("participants", [])
                winner_count = int(data.get("winner_count", 1))
                winner_ids = []
                
                if data.get("preselected_winners"):
                    winner_ids = data["preselected_winners"]
                    print(f"[РОЗЫГРЫШ] Используются предвыбранные победители")
                elif participants:
                    actual_winners_count = min(len(participants), winner_count)
                    winner_ids = random.sample(participants, actual_winners_count)
                    print(f"[РОЗЫГРЫШ] Выбрано {len(winner_ids)} случайных победителей")

                data["status"] = "finished" 
                data["winners"] = winner_ids
                data["finished_at"] = datetime.now(timezone.utc).isoformat()
                
                data.pop("preselected_winners", None)
                data.pop("preselected_by", None)
                data.pop("preselected_at", None)

                save_giveaway_data(data)
                await update_user_giveaway_embed(guild)

                log_channel = guild.get_channel(GIVEAWAY_LOG_CHANNEL_ID)
                if log_channel:
                    mentions_log = ", ".join([f"<@{wid}>" for wid in winner_ids]) if winner_ids else "Нет"
                    
                    log_embed = discord.Embed(
                        title="Розыгрыш завершен",
                        description=(
                            f"**Приз:** {data.get('prize')}\n"
                            f"**Победители:** {mentions_log}\n"
                            f"**Участников было:** {len(participants)}"
                        ),
                        color=discord.Color.green(),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    if guild.icon:
                        log_embed.set_thumbnail(url=guild.icon.url)
                    
                    log_embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)
                    await log_channel.send(embed=log_embed)
                    
                print(f"[РОЗЫГРЫШ] Розыгрыш завершен. Победителей: {len(winner_ids)}")

        except Exception as e:
            print(f"[ОШИБКА ТАЙМЕРА] {e}")
            import traceback
            traceback.print_exc()

    @check_giveaway_end.before_loop
    async def before_check_giveaway_end(self):
        await self.bot.wait_until_ready()
        print("[РОЗЫГРЫШ] Таймер запущен")


async def setup(bot):
    cog = GiveawayCog(bot)
    await bot.add_cog(cog)
    print("[РОЗЫГРЫШ] GiveawayCog загружен")