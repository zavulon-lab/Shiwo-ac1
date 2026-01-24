import discord
import time
from discord.ext import commands
from datetime import datetime, timezone

from config import (
    LOG_MESSAGES_CHANNEL_ID,
    LOG_VOICE_CHANNEL_ID,
    LOG_ROLES_CHANNEL_ID,
    LOG_NICKNAMES_CHANNEL_ID,
    LOG_MODERATION_CHANNEL_ID
)

class UserLogsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def send_log(self, channel_id: int, embed: discord.Embed):
        """Отправляет лог в указанный канал, если канал существует"""
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.send(embed=embed)
            except Exception as e:
                print(f"[USER_LOGS] Ошибка отправки в канал {channel_id}: {e}")

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return

        ts = int(time.time())
        embed = discord.Embed(
            title="Сообщение удалено",
            description=f"Автор: {message.author} ({message.author.id})\nКанал: {message.channel.mention}\nВремя события: <t:{ts}:R>",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Содержимое", value=message.content or "Контент отсутствует", inline=False)
        if message.attachments:
            embed.add_field(name="Вложения", value="\n".join(a.url for a in message.attachments), inline=False)
        
        embed.set_footer(text=f"User ID: {message.author.id}")
        await self.send_log(LOG_MESSAGES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content:
            return

        ts = int(time.time())
        embed = discord.Embed(
            title="Сообщение изменено",
            description=f"Автор: {before.author} ({before.author.id})\nКанал: {before.channel.mention}\nВремя события: <t:{ts}:R>",
            color=discord.Color.from_rgb(54, 57, 63),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Исходный текст", value=before.content or "Пусто", inline=False)
        embed.add_field(name="Новый текст", value=after.content or "Пусто", inline=False)
        
        embed.set_footer(text=f"User ID: {before.author.id}")
        await self.send_log(LOG_MESSAGES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return

        ts = int(time.time())
        embed = discord.Embed(timestamp=datetime.now(timezone.utc))
        embed.set_author(name=f"{member.display_name} ({member.id})", icon_url=member.display_avatar.url)

        if before.channel is None:
            embed.title = "Подключение к голосовому каналу"
            embed.description = f"Участник зашел в {after.channel.name}\nВремя: <t:{ts}:R>"
            embed.color = discord.Color.green()
        elif after.channel is None:
            embed.title = "Отключение от голосового канала"
            embed.description = f"Участник вышел из {before.channel.name}\nВремя: <t:{ts}:R>"
            embed.color = discord.Color.red()
        else:
            embed.title = "Перемещение между каналами"
            embed.description = f"Переход: {before.channel.name} -> {after.channel.name}\nВремя: <t:{ts}:R>"
            color=discord.Color.from_rgb(54, 57, 63)

        await self.send_log(LOG_VOICE_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        ts = int(time.time())
        
        if before.display_name != after.display_name:
            embed = discord.Embed(
                title="Изменение никнейма",
                description=f"Участник: {after.mention} ({after.id})\nВремя: <t:{ts}:R>",
                color=discord.Color.from_rgb(54, 57, 63),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Прежний", value=before.display_name, inline=True)
            embed.add_field(name="Новый", value=after.display_name, inline=True)
            await self.send_log(LOG_NICKNAMES_CHANNEL_ID, embed)

        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            if added or removed:
                embed = discord.Embed(
                    title="Обновление ролей пользователя",
                    description=f"Участник: {after.mention} ({after.id})\nВремя: <t:{ts}:R>",
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=datetime.now(timezone.utc)
                )
                if added:
                    embed.add_field(name="Выданы", value=", ".join(r.mention for r in added), inline=False)
                if removed:
                    embed.add_field(name="Сняты", value=", ".join(r.mention for r in removed), inline=False)
                
                await self.send_log(LOG_ROLES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Вычисляем возраст аккаунта
        now = datetime.now(timezone.utc)
        diff = now - member.created_at
        years = diff.days // 365
        days = diff.days % 365
        
        # Формируем строку возраста
        age_str = f"**{years} лет, {days} дней**" if years > 0 else f"**{days} дней**"

        embed = discord.Embed(
            # Описание сверху (как на скрине: иконка + упоминание + текст)
            description=f"<:emoji:1463115113115680873> {member.mention} присоединился в Discord сервер",
            color=discord.Color.green() # Зеленая полоска слева
        )

        # Поле "Информация" (слева)
        info_value = (
            f"Участник: {member.mention}\n"
            f"<:link:123456789> login: {member.name}\n"
            f"<:id_card:123456789> ID: {member.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)

        # Поле "Возраст аккаунта" (справа)
        # Используйте свой ID эмодзи песочных часов или секундомера
        embed.add_field(
            name="Возраст аккаунта", 
            value=f"<:clock:123456789> {age_str}", 
            inline=True
        )

        # Нижняя строка с количеством участников
        embed.set_footer(text=f"Количество участников: {member.guild.member_count}")

        # Отправляем в канал модерации или приветствий (добавьте ID в config)
        await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        now = datetime.now(timezone.utc)
        diff = now - member.created_at
        years = diff.days // 365
        days = diff.days % 365
        age_str = f"**{years} лет, {days} дней**" if years > 0 else f"**{days} дней**"

        embed = discord.Embed(
            description=f"<:leave_icon:123456789> {member.mention} вышел с Discord сервера",
            color=discord.Color.red() # Красная полоска
        )

        info_value = (
            f"Участник: {member.mention}\n"
            f"<:link:123456789> login: {member.name}\n"
            f"<:id_card:123456789> ID: {member.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        
        # Смайлик руки на прощание
        embed.add_field(
            name="Возраст аккаунта", 
            value=f"<:wave:123456789> {age_str}", 
            inline=True
        )

        await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        ts = int(time.time())
        embed = discord.Embed(
            title="Создана роль",
            description=f"Название: {role.name}\nID: {role.id}\nСоздана: <t:{ts}:R>",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        perms = role.permissions
        embed.add_field(
            name="Основные полномочия",
            value=(
                f"Администратор: {'Да' if perms.administrator else 'Нет'}\n"
                f"Управление сервером: {'Да' if perms.manage_guild else 'Нет'}\n"
                f"Управление ролями: {'Да' if perms.manage_roles else 'Нет'}"
            ),
            inline=False
        )
        await self.send_log(LOG_ROLES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        ts = int(time.time())
        embed = discord.Embed(
            title="Удалена роль",
            description=f"Название: {role.name}\nID: {role.id}\nУдалена: <t:{ts}:R>",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        await self.send_log(LOG_ROLES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        ts = int(time.time())
        embed = discord.Embed(
            title="Блокировка пользователя",
            description=f"Участник: {user} ({user.id})\nВремя: <t:{ts}:R>",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        ts = int(time.time())
        async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id:
                embed = discord.Embed(
                    title="Исключение пользователя (Кик)",
                    description=f"Участник: {member} ({member.id})\nМодератор: {entry.user}\nВремя: <t:{ts}:R>",
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=datetime.now(timezone.utc)
                )
                await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)
                return

async def setup(bot: commands.Bot):
    await bot.add_cog(UserLogsCog(bot))