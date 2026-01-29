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
            description=f"<:delete:1466443655291342901> **Сообщение удалено**",
            color=discord.Color.red()
        )
        
        info_value = (
            f"Участник: {message.author.mention}\n"
            f"<:link:1466443659502289072> login: {message.author.name}\n"
            f"<:id_card:1466443657191358506> ID: {message.author.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        
        channel_value = (
            f"<:link:1466443659502289072> Канал: {message.channel.mention}\n"
            f"<:present:1466443614002352240> Время: <t:{ts}:R>"
        )
        embed.add_field(name="Детали", value=channel_value, inline=True)
        embed.add_field(name="Содержимое", value=message.content or "Контент отсутствует", inline=False)
        
        if message.attachments:
            embed.add_field(name="Вложения", value="\n".join(a.url for a in message.attachments), inline=False)
        
        embed.set_thumbnail(url=message.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {message.author.id}")
        await self.send_log(LOG_MESSAGES_CHANNEL_ID, embed)


    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content:
            return

        ts = int(time.time())
        embed = discord.Embed(
            description=f"<:edit:1466443592573648906> **Сообщение изменено**",
            color=discord.Color.from_rgb(54, 57, 63)
        )
        
        info_value = (
            f"Участник: {before.author.mention}\n"
            f"<:link:1466443659502289072> login: {before.author.name}\n"
            f"<:id_card:1466443657191358506> ID: {before.author.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        
        channel_value = (
            f"<:link:1466443659502289072> Канал: {before.channel.mention}\n"
            f"<:present:1466443614002352240> Время: <t:{ts}:R>"
        )
        embed.add_field(name="Детали", value=channel_value, inline=True)
        embed.add_field(name="Было", value=before.content or "Пусто", inline=False)
        embed.add_field(name="Стало", value=after.content or "Пусто", inline=False)
        
        embed.set_thumbnail(url=before.author.display_avatar.url)
        embed.set_footer(text=f"User ID: {before.author.id}")
        await self.send_log(LOG_MESSAGES_CHANNEL_ID, embed)


    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if before.channel == after.channel:
            return

        ts = int(time.time())
        embed = discord.Embed()

        info_value = (
            f"Участник: {member.mention}\n"
            f"<:link:1466443659502289072> login: {member.name}\n"
            f"<:id_card:1466443657191358506> ID: {member.id}"
        )

        if before.channel is None:
            embed.description = f"<:join:1466443664040399076> **Подключение к голосовому каналу**"
            embed.color = discord.Color.green()
            channel_info = f"Канал: {after.channel.name}\n<:present:1466443614002352240> Время: <t:{ts}:R>"
        elif after.channel is None:
            embed.description = f"<:leave_icon:1466443661842845759> **Отключение от голосового канала**"
            embed.color = discord.Color.red()
            channel_info = f"Канал: {before.channel.name}\n<:present:1466443614002352240> Время: <t:{ts}:R>"
        else:
            embed.description = f"<:arrow:1466443664040399076> **Перемещение между каналами**"
            embed.color = discord.Color.from_rgb(54, 57, 63)
            channel_info = f"{before.channel.name} → {after.channel.name}\n<:present:1466443614002352240> Время: <t:{ts}:R>"

        embed.add_field(name="Информация", value=info_value, inline=True)
        embed.add_field(name="Детали", value=channel_info, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        
        await self.send_log(LOG_VOICE_CHANNEL_ID, embed)


    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        ts = int(time.time())
        
        if before.display_name != after.display_name:
            embed = discord.Embed(
                description=f"<:edit:1466443592573648906> **Изменение никнейма**",
                color=discord.Color.from_rgb(54, 57, 63)
            )
            
            info_value = (
                f"Участник: {after.mention}\n"
                f"<:link:1466443659502289072> login: {after.name}\n"
                f"<:id_card:1466443657191358506> ID: {after.id}"
            )
            embed.add_field(name="Информация", value=info_value, inline=True)
            
            change_value = (
                f"**Было:** {before.display_name}\n"
                f"**Стало:** {after.display_name}\n"
                f"<:present:1466443614002352240> Время: <t:{ts}:R>"
            )
            embed.add_field(name="Изменения", value=change_value, inline=True)
            embed.set_thumbnail(url=after.display_avatar.url)
            embed.set_footer(text=f"User ID: {after.id}")
            await self.send_log(LOG_NICKNAMES_CHANNEL_ID, embed)

        if before.roles != after.roles:
            added = [r for r in after.roles if r not in before.roles]
            removed = [r for r in before.roles if r not in after.roles]

            if added or removed:
                embed = discord.Embed(
                    description=f"<:roles:1466443586600964270> **Обновление ролей**",
                    color=discord.Color.from_rgb(54, 57, 63)
                )
                
                info_value = (
                    f"Участник: {after.mention}\n"
                    f"<:link:1466443659502289072> login: {after.name}\n"
                    f"<:id_card:1466443657191358506> ID: {after.id}"
                )
                embed.add_field(name="Информация", value=info_value, inline=True)
                moderator_value = "Не найден"
                async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id and entry.created_at.timestamp() >= (ts - 5):
                        moderator_value = f"{entry.user.mention}"
                        break

                embed.add_field(name="Модератор", value=moderator_value, inline=True)
                embed.add_field(name="Время", value=f"<:present:1466443614002352240> <t:{ts}:R>", inline=True)
                
                if added:
                    embed.add_field(name="<:plus:1466443582268244156> Выданы", value=", ".join(r.mention for r in added), inline=False)
                if removed:
                    embed.add_field(name="<:minus:1466443584130650282> Сняты", value=", ".join(r.mention for r in removed), inline=False)
                
                embed.set_thumbnail(url=after.display_avatar.url)
                embed.set_footer(text=f"User ID: {after.id}")
                
                await self.send_log(LOG_ROLES_CHANNEL_ID, embed)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        now = datetime.now(timezone.utc)
        diff = now - member.created_at
        years = diff.days // 365
        days = diff.days % 365
        
        
        age_str = f"**{years} лет, {days} дней**" if years > 0 else f"**{days} дней**"

        embed = discord.Embed(
            description=f"<:emoji:1466443664040399076> {member.mention} присоединился в Discord сервер",
            color=discord.Color.green()
        )

        
        info_value = (
            f"Участник: {member.mention}\n"
            f"<:link:1466443659502289072> login: {member.name}\n"
            f"<:id_card:1466443657191358506> ID: {member.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)

        
        embed.add_field(
            name="Возраст аккаунта", 
            value=f"<:present:1466443614002352240> {age_str}", 
            inline=True
        )

        
        embed.set_footer(text=f"Количество участников: {member.guild.member_count}")

        await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)


    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        ts = int(time.time())
        now = datetime.now(timezone.utc)
        diff = now - member.created_at
        years = diff.days // 365
        days = diff.days % 365
        age_str = f"**{years} лет, {days} дней**" if years > 0 else f"**{days} дней**"

        kicked = False
        async for entry in member.guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
            if entry.target.id == member.id and (datetime.now(timezone.utc) - entry.created_at).total_seconds() < 5:
                embed = discord.Embed(
                    description=f"<:ban:1466443661842845759> **Исключение пользователя (Кик)**",
                    color=discord.Color.red()
                )
                
                info_value = (
                    f"Участник: {member.mention}\n"
                    f"<:link:1466443659502289072> login: {member.name}\n"
                    f"<:id_card:1466443657191358506> ID: {member.id}"
                )
                embed.add_field(name="Информация", value=info_value, inline=True)
                
                moderator_value = (
                    f"Модератор: {entry.user.mention}\n"
                    f"<:present:1466443614002352240> Время: <t:{ts}:R>"
                )
                embed.add_field(name="Детали", value=moderator_value, inline=True)
                
                embed.set_footer(text=f"User ID: {member.id}")
                
                await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)
                kicked = True
                break

        if not kicked:
            embed = discord.Embed(
                description=f"<:leave_icon:1466443661842845759> {member.mention} вышел с Discord сервера",
                color=discord.Color.red()
            )
            
            info_value = (
                f"Участник: {member.mention}\n"
                f"<:link:1466443659502289072> login: {member.name}\n"
                f"<:id_card:1466443657191358506> ID: {member.id}"
            )
            embed.add_field(name="Информация", value=info_value, inline=True)
            
            embed.add_field(
                name="Возраст аккаунта", 
                value=f"<:present:1466443614002352240> {age_str}", 
                inline=True
            )
            
            embed.set_footer(text=f"Количество участников: {member.guild.member_count}")
            
            await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)



    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        ts = int(time.time())
        embed = discord.Embed(
            description=f"<:plus:1466443664040399076> **Создана роль**",
            color=discord.Color.green()
        )
        
        info_value = (
            f"**Название:** {role.name}\n"
            f"<:id_card:1466443657191358506> ID: {role.id}\n"
            f"<:present:1466443614002352240> Время: <t:{ts}:R>"
        )
        embed.add_field(name="Информация", value=info_value, inline=False)
        
        perms = role.permissions
        embed.add_field(
            name="<:shield:1466443664040399076> Полномочия",
            value=(
                f"Администратор: {'✅' if perms.administrator else '❌'}\n"
                f"Управление сервером: {'✅' if perms.manage_guild else '❌'}\n"
                f"Управление ролями: {'✅' if perms.manage_roles else '❌'}"
            ),
            inline=False
        )
        await self.send_log(LOG_ROLES_CHANNEL_ID, embed)


    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        ts = int(time.time())
        embed = discord.Embed(
            description=f"<:minus:1466443664040399076> **Удалена роль**",
            color=discord.Color.red()
        )
        
        info_value = (
            f"**Название:** {role.name}\n"
            f"<:id_card:1466443657191358506> ID: {role.id}\n"
            f"<:present:1466443614002352240> Время: <t:{ts}:R>"
        )
        embed.add_field(name="Информация", value=info_value, inline=False)
        embed.set_footer(text=f"Role ID: {role.id}")
        await self.send_log(LOG_ROLES_CHANNEL_ID, embed)


    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        ts = int(time.time())
        embed = discord.Embed(
            description=f"<:ban:1466443661842845759> **Блокировка пользователя**",
            color=discord.Color.dark_red()
        )
        
        info_value = (
            f"Участник: {user.mention}\n"
            f"<:link:1466443659502289072> login: {user.name}\n"
            f"<:id_card:1466443657191358506> ID: {user.id}"
        )
        embed.add_field(name="Информация", value=info_value, inline=True)
        embed.add_field(name="Время", value=f"<:present:1466443614002352240> <t:{ts}:R>", inline=True)
        
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text=f"User ID: {user.id}")
        await self.send_log(LOG_MODERATION_CHANNEL_ID, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(UserLogsCog(bot), override=True)
