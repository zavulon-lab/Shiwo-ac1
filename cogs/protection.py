import time
import discord
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from discord import Interaction, ButtonStyle, SelectOption, AuditLogEntry, Color
from datetime import datetime, timezone
import sqlite3
from pathlib import Path
import asyncio

from config import PROTECTION_ADMIN_CHANNEL_ID, PROTECTION_LOG_CHANNEL_ID, SUPPORT_ROLE_ID

DB_PATH = Path("protection.db")



def init_protection_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS protection_config (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
   
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            user_id INTEGER PRIMARY KEY,
            total_warns INTEGER DEFAULT 0,
            actions_progress TEXT
        )
    ''')
    
    conn.commit()
    conn.close()


def load_config():
    
    init_protection_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT value FROM protection_config WHERE key = ?', ('config',))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        import json
        return json.loads(row[0])
    
    import json
    default = {
        "events": {
            "channel_delete": "ban",
            "channel_create": "ban",
            "webhook_create": "ban",
            "webhook_send": "kick",
            "ban_member": "kick",
            "kick_member": "kick",
            "everyone_ping": "kick",
            "here_ping": "kick"
        },
        "whitelist": [],
        "panel_message_id": None
    }
    save_config(default)
    return default


def save_config(config):
    
    import json
    init_protection_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        'INSERT OR REPLACE INTO protection_config (key, value) VALUES (?, ?)',
        ('config', json.dumps(config, ensure_ascii=False))
    )
    
    conn.commit()
    conn.close()


def load_violations():
    
    init_protection_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, total_warns, actions_progress FROM violations')
    rows = cursor.fetchall()
    conn.close()
    
    import json
    violations = {}
    for user_id, total_warns, actions_progress_str in rows:
        violations[str(user_id)] = {
            "total_warns": total_warns,
            "actions_progress": json.loads(actions_progress_str) if actions_progress_str else {}
        }
    
    return violations


def save_violations(data):
   
    import json
    init_protection_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM violations')
    
    for user_id_str, violation_data in data.items():
        user_id = int(user_id_str)
        total_warns = violation_data.get("total_warns", 0)
        actions_progress = json.dumps(violation_data.get("actions_progress", {}))
        
        cursor.execute(
            'INSERT INTO violations (user_id, total_warns, actions_progress) VALUES (?, ?, ?)',
            (user_id, total_warns, actions_progress)
        )
    
    conn.commit()
    conn.close()


def load_whitelist():
    
    init_protection_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id FROM whitelist')
    rows = cursor.fetchall()
    conn.close()
    
    return [row[0] for row in rows]


def add_to_whitelist(user_id):
   
    init_protection_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)', (user_id,))
    
    conn.commit()
    conn.close()


def remove_from_whitelist(user_id):
   
    init_protection_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM whitelist WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()


EVENT_EMOJIS = {
    "channel_delete": "<:emoji_name:1463122455961927711>",
    "channel_create": "<:plus_icon:1463122449616081077>",
    "webhook_create": "<:webhook_icon:1463122459510309056>",
    "webhook_send": "<:send_icon:1463122460353237013>",
    "ban_member": "<:ban_icon:1463122461750198323>",
    "kick_member": "<:kick_icon:1463122451704713246>",
    "everyone_ping": "<:everyone_icon:1463122447791296648>",
    "here_ping": "<:here_icon:1463122457824067755>"
}

ACTION_NAMES = {
    "ban": "Бан",
    "kick": "Кик",
    "warn": "warn",
    "tempban": "Врем. бан",
    "none": "Без действий",
    "delete": "Удалять"
}

ACTION_EMOJIS = {
    "ban": "<:emoji_name:1463263884810125527>",
    "kick": "<:emoji_name:1463263884810125527>",
    "warn": "<:emoji_name:1463263883056644181>",
    "tempban": "<:emoji_name:1463263883056644181>",
    "none": "<:emoji_name:1463263885887799533>"
}

config = load_config()

EVENTS = {
    "channel_delete": "Удаление канала",
    "channel_create": "Создание канала",
    "webhook_create": "Создание вебхука",
    "webhook_send": "Отправка от вебхука",
    "ban_member": "Бан участника",
    "kick_member": "Кик участника",
    "everyone_ping": "Пинг @everyone",
    "here_ping": "Пинг @here"
}


class TempBanModal(Modal, title="Временный бан"):
    duration = TextInput(label="Длительность (секунды)", placeholder="Например: 3600 (1 час)", required=True)

    def __init__(self, user):
        super().__init__()
        self.user = user

    async def on_submit(self, interaction: Interaction):
        try:
            seconds = int(self.duration.value.strip())
            if seconds <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Введите положительное число секунд.", ephemeral=True)
            return

        reason = f"Автоматическая защита: временный бан на {seconds} секунд"
        try:
            await interaction.guild.ban(self.user, reason=reason)
            await interaction.response.send_message(f"{self.user} забанен на {seconds} секунд.", ephemeral=True)

            await asyncio.sleep(seconds)
            await interaction.guild.unban(self.user, reason="Окончание временного бана")
            log_channel = interaction.guild.get_channel(PROTECTION_LOG_CHANNEL_ID)
            if log_channel:
                await log_channel.send(f"Временный бан {self.user} истёк.")
        except Exception as e:
            await interaction.response.send_message(f"Ошибка: {e}", ephemeral=True)


class ActionSelect(View):
    def __init__(self, event_key):
        super().__init__(timeout=300)
        self.event_key = event_key

        select = Select(
            placeholder="Выберите действие",
            options=[
                SelectOption(label="Бан", value="ban", emoji="<:emoji_name:1463263884810125527>"),
                SelectOption(label="Кик", value="kick", emoji="<:emoji_name:1463263884810125527>"),
                SelectOption(label="Предупреждение", value="warn", emoji="<:emoji_name:1463263883056644181>"),
                SelectOption(label="Временный бан", value="tempban", emoji="<:emoji_name:1463263883056644181>"),
                SelectOption(label="Без действий", value="none", emoji="<:emoji_name:1463263885887799533>")
            ]
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        action = interaction.data["values"][0]
        
        if action == "none":
            config["events"][self.event_key] = {"action": "none", "limit": 1}
            save_config(config)
            
            event_name = EVENTS.get(self.event_key, self.event_key)
            embed = discord.Embed(
                title="Защита отключена",
                description=f"Для события **`{event_name}`** теперь не применяются никакие санкции.",
                color=discord.Color.from_rgb(54, 57, 63)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await update_protection_panel(interaction.guild)
        
        else:
            await interaction.response.send_modal(ActionConfigModal(self.event_key, action))


class WhitelistModal(Modal, title="Добавить в вайтлист"):
    user_id = TextInput(label="ID пользователя", placeholder="Введите ID", required=True)

    async def on_submit(self, interaction: Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            await interaction.response.send_message("Неверный ID.", ephemeral=True)
            return

        whitelist = load_whitelist()
        if uid in whitelist:
            await interaction.response.send_message("Уже в вайтлисте.", ephemeral=True)
            return

        add_to_whitelist(uid)
        
        config["whitelist"] = load_whitelist()
        save_config(config)
        
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else "Неизвестно"
        await interaction.response.send_message(f" {name} (`{uid}`) добавлен в вайтлист.", ephemeral=True)
        await update_protection_panel(interaction.guild)


class RemoveWhitelistModal(Modal, title="Удалить из вайтлиста"):
    user_id = TextInput(label="ID пользователя", placeholder="Введите ID для удаления", required=True)

    async def on_submit(self, interaction: Interaction):
        try:
            uid = int(self.user_id.value.strip())
        except ValueError:
            await interaction.response.send_message(" Неверный ID. Введите только цифры.", ephemeral=True)
            return

        whitelist = load_whitelist()
        if uid not in whitelist:
            await interaction.response.send_message(" Этот ID не найден в вайтлисте.", ephemeral=True)
            return

        remove_from_whitelist(uid)
        
        config["whitelist"] = load_whitelist()
        save_config(config)
        
        member = interaction.guild.get_member(uid)
        name = member.display_name if member else "Неизвестно"
        await interaction.response.send_message(f" Пользователь **{name}** (`{uid}`) удалён из вайтлиста.", ephemeral=True)
        await update_protection_panel(interaction.guild)


class ProtectionConfigView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Выберите событие для настройки",
        custom_id="protection_event_select",
        options=[
            discord.SelectOption(
                label="Удаление канала", 
                value="channel_delete",
                description="Массовое удаление текстовых каналов",
                emoji="<:emoji_name:1463122455961927711>"
            ),
            discord.SelectOption(
                label="Создание канала", 
                value="channel_create",
                description="Массовое создание текстовых каналов ",
                emoji="<:plus_icon:1463122449616081077>"
            ),
            discord.SelectOption(
                label="Создание вебхука", 
                value="webhook_create",
                description="Создание интеграции & Вебхука",
                emoji="<:webhook_icon:1463122459510309056>"
            ),
            discord.SelectOption(
                label="Отправка от вебхука", 
                value="webhook_send",
                description="Взаимодействие с URL вебхука",
                emoji="<:send_icon:1463122460353237013>"
            ),
            discord.SelectOption(
                label="Бан участника", 
                value="ban_member",
                description="Реакция на массовые блокировки участников",
                emoji="<:ban_icon:1463122461750198323>"
            ),
            discord.SelectOption(
                label="Кик участника", 
                value="kick_member",
                description="Защита от массовых исключений участников",
                emoji="<:kick_icon:1463122451704713246>"
            ),
            discord.SelectOption(
                label="Пинг @everyone", 
                value="everyone_ping",
                description="Ограничение упоминаний роли @everyone",
                emoji="<:everyone_icon:1463122447791296648>"
            ),
            discord.SelectOption(
                label="Пинг @here", 
                value="here_ping",
                description="Ограничение упоминаний роли @here",
                emoji="<:here_icon:1463122457824067755>"
            )
        ]
    )
    async def event_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        event_key = select.values[0]
        view = ActionSelect(event_key)
        await interaction.response.send_message(
            f"Настройка: **{EVENTS.get(event_key, event_key)}**", 
            view=view, 
            ephemeral=True
        )

    @discord.ui.button(label="Вайтлист", style=ButtonStyle.grey, custom_id="protection_whitelist")
    async def whitelist_button(self, interaction: Interaction, button: Button):
        if interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Только владелец сервера может управлять вайтлистом.", ephemeral=True)
            return
        
        whitelist = load_whitelist()
        text = "Вайтлист пуст." if not whitelist else "\n".join(f"• <@{uid}> (`{uid}`)" for uid in whitelist[:20])
        if len(whitelist) > 20:
            text += f"\n... и ещё {len(whitelist) - 20}"
        embed = discord.Embed(title="Вайтлист защиты", description=text, color=discord.Color.from_rgb(54, 57, 63))
        view = WhitelistView(interaction.guild.owner.id) 
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)



class WhitelistView(View):
    def __init__(self, owner_id):
        super().__init__(timeout=300)
        self.owner_id = owner_id

    @discord.ui.button(label="Добавить", style=ButtonStyle.green)
    async def add(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец сервера может это делать.", ephemeral=True)
            return
        await interaction.response.send_modal(WhitelistModal())
    
    @discord.ui.button(label="Удалить пользователя", style=ButtonStyle.red)
    async def remove(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Только владелец сервера может это делать.", ephemeral=True)
            return
        await interaction.response.send_modal(RemoveWhitelistModal())



async def update_protection_panel(guild: discord.Guild):
    channel = guild.get_channel(PROTECTION_ADMIN_CHANNEL_ID)
    if not channel:
        print("[ЗАЩИТА] Админский канал не найден!")
        return

    try:
        config_lines = []
        for event_key, data in config["events"].items():
            if isinstance(data, dict):
                action = data.get("action", "none")
                limit = data.get("limit", 1)
                duration = data.get("duration", 0)
            else:
                action = data
                limit = 1
                duration = 0

            event_name = EVENTS.get(event_key, event_key)
            action_name = ACTION_NAMES.get(action, action)
            event_emoji = EVENT_EMOJIS.get(event_key, "⚙️")
            
            action_emoji = ACTION_EMOJIS.get(action, "❓")
            
            time_info = f" ({duration}м)" if action == "tempban" else ""

            if action != "none":
                limit_text = f"  {action_emoji} `{action_name}{time_info}` `{limit}`"
            else:
                limit_text = f"  {action_emoji} `{action_name}`"

            line = f"{event_emoji} **{event_name}**{limit_text}"
            config_lines.append(line)

        config_text = "\n".join(config_lines)

        embed = discord.Embed(color=discord.Color.from_rgb(54, 57, 63))
        embed.description = "## Панель управления защитой"

        current_field_value = ""
        first_field = True

        for line in config_lines:
            if len(current_field_value) + len(line) + 1 > 1020:
                embed.add_field(
                    name="**```Конфигурация защиты```**" if first_field else "\u200b",
                    value=current_field_value,
                    inline=False
                )
                current_field_value = line + "\n"
                first_field = False
            else:
                current_field_value += line + "\n"

        if current_field_value:
            embed.add_field(
                name="**```Конфигурация защиты```**" if first_field else "\u200b",
                value=current_field_value,
                inline=False
            )

        terms_text = (
            "**Бан** — Блокировка и снятие ролей\n"
            "**Кик** — Исключение из сервера\n"
            "**Без действий** — Санкции отключены\n"
            "**Warn** — Уведомление, затем кик"
        )
        embed.add_field(name="\u200b", value=f"```Термины```\n>>> {terms_text}", inline=False)

        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
            embed.set_footer(text=f"{guild.name}", icon_url=guild.icon.url)
        else:
            embed.set_footer(text=f"{guild.name}")

        view = ProtectionConfigView()

        message_id = config.get("panel_message_id")
        panel_processed = False

        if message_id:
            try:
                old_message = await channel.fetch_message(message_id)
                await old_message.edit(embed=embed, view=view)
                panel_processed = True
                print(f"[ЗАЩИТА] Панель обновлена (ID: {message_id})")
            except (discord.NotFound, discord.HTTPException):
                print("[ЗАЩИТА] Старая панель не найдена (удалена), создаю новую...")
                panel_processed = False

        if not panel_processed:
            new_message = await channel.send(embed=embed, view=view)
            config["panel_message_id"] = new_message.id
            save_config(config)
            print(f"[ЗАЩИТА] Новая панель успешно отправлена. ID: {new_message.id}")

    except Exception as e:
        print(f"[КРИТИЧЕСКАЯ ОШИБКА ПАНЕЛИ] {e}")


class ActionConfigModal(Modal):
    def __init__(self, event_key, action):
        super().__init__(title=f"Настройка: {EVENTS.get(event_key)}")
        self.event_key = event_key
        self.action = action
        
        self.limit_input = TextInput(
            label="Лимит срабатываний",
            placeholder="Через сколько действий наказать? (например: 3)",
            default="1", min_length=1, max_length=3
        )
        self.add_item(self.limit_input)

        if self.action == "tempban":
            self.time_input = TextInput(
                label="Длительность (в минутах)",
                placeholder="Например: 60 (1 час), максимум 40320 (28 дней)",
                default="60", min_length=1, max_length=6
            )
            self.add_item(self.time_input)

    async def on_submit(self, interaction: Interaction):
        try:
            limit_val = int(self.limit_input.value.strip())
            duration_val = 0
            if self.action == "tempban":
                duration_val = int(self.time_input.value.strip())
                if duration_val > 40320: duration_val = 40320
            
            if limit_val < 1: raise ValueError
        except ValueError:
            return await interaction.response.send_message("Ошибка: Введите корректные числа.", ephemeral=True)

        config["events"][self.event_key] = {
            "action": self.action,
            "limit": limit_val,
            "duration": duration_val
        }
        save_config(config)

        time_text = f"\nВремя изоляции: `{duration_val}` мин." if self.action == "tempban" else ""
        
        embed = discord.Embed(
            title="⚙️ Конфигурация обновлена",
            description=(
                f"Событие: **{EVENTS.get(self.event_key)}**\n"
                f"Наказание: `{ACTION_NAMES.get(self.action)}`\n"
                f"Лимит действий: <:limit_icon:1463143604406190174> `{limit_val}`" + time_text
            ),
            color=discord.Color.from_rgb(54, 57, 63)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await update_protection_panel(interaction.guild)


class ProtectionCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(ProtectionConfigView())
        self.violations = load_violations()
        self.user_messages = {}
        
        init_protection_db()

    async def setup_protection_panel(self):
        
        await self.bot.wait_until_ready()
        
        self.bot.add_view(ProtectionConfigView())

        for guild in self.bot.guilds:
            await update_protection_panel(guild)
            print(f"[ЗАЩИТА] Панель инициализирована для сервера: {guild.name}")

    async def handle_action(self, entry: AuditLogEntry = None, message: discord.Message = None):
        user = entry.user if entry else message.author
        guild = entry.guild if entry else message.guild

        whitelist = load_whitelist()
        
        if user.bot or user == guild.owner or user.id in whitelist:
            return

        action_type = None
        if entry:
            mapping = {
                discord.AuditLogAction.channel_delete: "channel_delete",
                discord.AuditLogAction.channel_create: "channel_create",
                discord.AuditLogAction.webhook_create: "webhook_create",
                discord.AuditLogAction.webhook_update: "webhook_send",
                discord.AuditLogAction.ban: "ban_member",
                discord.AuditLogAction.kick: "kick_member"
            }
            action_type = mapping.get(entry.action)
        elif message and (message.mention_everyone or "@here" in message.content):
            action_type = "everyone_ping" if "@everyone" in message.content else "here_ping"

        if not action_type:
            return

        setting_raw = config["events"].get(action_type, "none")
        if isinstance(setting_raw, dict):
            setting = setting_raw.get("action", "none")
            limit = int(setting_raw.get("limit", 1))
        else:
            setting = setting_raw
            limit = 1

        if setting == "none":
            return

        uid_str = str(user.id)
        if uid_str not in self.violations:
            self.violations[uid_str] = {"total_warns": 0, "actions_progress": {}}
        
        progress = self.violations[uid_str]["actions_progress"].get(action_type, 0) + 1
        self.violations[uid_str]["actions_progress"][action_type] = progress
        save_violations(self.violations)
       
        if progress < limit:
            return 
        
        self.violations[uid_str]["actions_progress"][action_type] = 0
        self.violations[uid_str]["total_warns"] += 1
        total_warns = self.violations[uid_str]["total_warns"]
        save_violations(self.violations)

        punishment = "без наказания"
        success = False     
        try:
           
            if setting == "ban":
                await guild.ban(user, reason=f"Защита: Лимит {limit} для {action_type}")
                punishment = "заблокирован"
                success = True
            
            elif setting == "kick":
                await guild.kick(user, reason=f"Защита: Лимит {limit} для {action_type}")
                punishment = "кикнут"
                success = True

            elif setting == "warn":
               
                if total_warns == 1:
                    embed_warn = discord.Embed(
                        title="Предупреждение системы защиты",
                        description=f"Вы превысили лимит действия: **{EVENTS.get(action_type)}**.",
                        color=discord.Color.orange()
                    )
                    embed_warn.add_field(name="Статус", value="**[1 / 2]**", inline=True)
                    embed_warn.set_footer(text="Любое следующее превышение лимитов приведет к кику.")
                    
                    try:
                        await user.send(embed=embed_warn)
                        punishment = "[1/2]"
                    except:
                        punishment = "[1/2] (ЛС закрыты)"
                    success = True

                elif total_warns >= 2:
                    try:
                        kick_notice = discord.Embed(
                            title="Вы были исключены",
                            description=f"Кик с сервера **{guild.name}** за повторное нарушение правил.",
                            color=discord.Color.red()
                        )
                        await user.send(embed=kick_notice)
                    except: pass

                    await guild.kick(user, reason=f"Защита: Суммарный лимит нарушений [2/2]")
                    punishment = "кикнут (стак нарушений)"
                    
                    self.violations[uid_str] = {"total_warns": 0, "actions_progress": {}}
                    save_violations(self.violations)
                    success = True
            
            elif setting == "tempban":
                duration_min = int(setting_raw.get("duration", 60))
                until = datetime.now(timezone.utc) + discord.utils.datetime.timedelta(minutes=duration_min)
                
                try:
                    await user.timeout(until, reason=f"Защита: Лимит {limit} для {action_type}")
                    punishment = f"изоляция на {duration_min} мин."
                    success = True
                except discord.Forbidden:
                    await guild.ban(user, reason=f"Защита: Не удалось выдать таймаут, выдан бан. Лимит {limit}")
                    punishment = "забанен (ошибка прав таймаута)"
                    success = True
            
            if message and success:
                try: await message.delete()
                except: pass

        except discord.Forbidden:
            print(f"[ОШИБКА] Недостаточно прав для наказания {user.id}")
        
        if success:
            log_channel = guild.get_channel(PROTECTION_LOG_CHANNEL_ID)
            if log_channel:
                log_embed = discord.Embed(title="Сработала защита", color=Color.red())
                log_embed.add_field(name="Нарушитель", value=f"{user.mention} (`{user.id}`)")
                log_embed.add_field(name="Событие", value=EVENTS.get(action_type, action_type))
                log_embed.add_field(name="Наказание", value=punishment)
                log_embed.timestamp = datetime.now(timezone.utc)
                await log_channel.send(embed=log_embed)

    @commands.Cog.listener()
    async def on_audit_log_entry_create(self, entry: AuditLogEntry):
        await self.handle_action(entry=entry)  
     
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        
        whitelist = load_whitelist()
        if message.author.guild_permissions.administrator or any(role.id == SUPPORT_ROLE_ID for role in message.author.roles):
            await self.handle_action(message=message)
            return
        
        
        if "discord.gg/" in message.content or "discord.com/invite" in message.content:
            try:
                await message.delete()
            except:
                pass
            return
        
        if "@everyone" in message.content or "@here" in message.content:
            try:
                await message.delete()
            except:
                pass
            return
        
        uid = message.author.id
        now = time.time()
        
        if uid not in self.user_messages:
            self.user_messages[uid] = []
        
        self.user_messages[uid] = [t for t in self.user_messages[uid] if now - t < 8]
        self.user_messages[uid].append(now)
        
        if len(self.user_messages[uid]) >= 5:
            try:
                until = datetime.now(timezone.utc) + timedelta(minutes=5)
                await message.author.timeout(until, reason="Пассивная защита: спам сообщениями")
                
                self.user_messages[uid] = []
            except:
                pass
            return

        
        await self.handle_action(message=message)


async def setup(bot):
    cog = ProtectionCog(bot)
    await bot.add_cog(cog)