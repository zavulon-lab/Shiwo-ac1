import discord
from discord.ext import commands, tasks
from discord.ui import Modal, TextInput, View, Button
from discord import Interaction, ButtonStyle, Color, Guild
from datetime import datetime, timezone
import random
import time

from config import (
    GIVEAWAY_USER_CHANNEL_ID,
    GIVEAWAY_ADMIN_CHANNEL_ID,
    GIVEAWAY_LOG_CHANNEL_ID,
    MAX_WINNERS
)

from giveaway_data import load_giveaway_data, save_giveaway_data


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

        temp_data = {
            "description": self.description.value,
            "prize": self.prize.value,
            "sponsor": self.sponsor.value,
            "winner_count": w_count,
            "end_time": end_dt.strftime("%Y-%m-%d %H:%M"),
            "participants": load_giveaway_data().get("participants", []),
            "status": "active"
        }
        preview_embed = discord.Embed(
            title="Предпросмотр розыгрыша",
            description=temp_data["description"],
            color=Color.gold()
        )
        preview_embed.add_field(name="Приз", value=temp_data["prize"], inline=True)
        preview_embed.add_field(name="Спонсор", value=temp_data["sponsor"], inline=True)
        preview_embed.add_field(name="Окончание", value=temp_data["end_time"], inline=False)
        preview_embed.add_field(name="Участников", value=str(len(temp_data["participants"])), inline=False)

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
        winners_objects = []
        mentions_list = []

        for wid in winner_ids:
            user = guild.get_member(wid)
            if user:
                winners_objects.append(user)
                mentions_list.append(user.mention)
            else:
                mentions_list.append(f"ID {wid} (не найден)")

        # 5. Логирование (сохраняем вашу структуру)
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

        await update_user_giveaway_embed(guild)

        await interaction.response.send_message(
            f"Успешно! Выбрано победителей: **{len(winner_ids)}**.\n"
            f"Они будут объявлены автоматически в назначенное время.",
            ephemeral=True
        )


class GiveawayPreviewView(View):
    def __init__(self, temp_data):
        super().__init__(timeout=300)
        self.temp_data = temp_data

    @discord.ui.button(label="Подтвердить", style=ButtonStyle.green)
    async def confirm(self, interaction: Interaction, button: Button):
        print(f"Кнопка 'Подтвердить' нажата пользователем: {interaction.user.id}")
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
            print(f"Данные нового розыгрыша {new_data['id']} сохранены.")

            
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

            await interaction.response.send_message("Розыгрыш успешно запущен! Старые данные удалены.", ephemeral=True)
            self.stop()

        except Exception as e:
            print(f"Ошибка в confirm: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"Ошибка: {e}", ephemeral=True)
            else:
                await interaction.followup.send(f"Ошибка: {e}", ephemeral=True)

    @discord.ui.button(label="Отредактировать заново", style=ButtonStyle.grey)
    async def edit_again(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(GiveawayEditModal())
        self.stop()


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
        num_participants = len(participants)
        if num_participants == 0:
            await interaction.response.send_message("Нет участников в розыгрыше.", ephemeral=True)
            return

        list_text = "\n".join(f"{i+1}. <@{uid}>" for i, uid in enumerate(participants[:50]))
        if num_participants > 50:
            list_text += f"\n... и ещё {num_participants - 50} участников"

        embed = discord.Embed(
            title="Список участников розыгрыша",
            description=list_text,
            color=discord.Color.from_rgb(54, 57, 63)
        )
        embed.set_footer(text=f"Всего: {num_participants}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GiveawayAdminView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Редактировать розыгрыш", style=ButtonStyle.primary, custom_id="giveaway_edit")
    async def edit_giveaway(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Только администраторы.", ephemeral=True)
            return
        await interaction.response.send_modal(GiveawayEditModal())

    @discord.ui.button(label="Выбрать победителя", style=ButtonStyle.success, custom_id="giveaway_select_winner")
    async def select_winner(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Только администраторы.", ephemeral=True)
            return

        data = load_giveaway_data()
        if not data:
            await interaction.response.send_message("Нет активного розыгрыша.", ephemeral=True)
            return

        await interaction.response.send_modal(WinnerSelectModal())


async def update_user_giveaway_embed(guild: Guild):
    data = load_giveaway_data()
    channel = guild.get_channel(GIVEAWAY_USER_CHANNEL_ID)
    if not channel: return

    fixed_message_id = data.get("fixed_message_id")
    message = None
    if fixed_message_id:
        try: message = await channel.fetch_message(fixed_message_id)
        except: message = None

    if data and data.get("status") != "finished":
        embed = discord.Embed(
            title="РОЗЫГРЫШ",
            description=f"```\n{data.get('description')}\n```",
            color=discord.Color.from_rgb(54, 57, 63) 
        )
        
        embed.add_field(name="Приз", value=f"**```{data.get('prize')}```**", inline=False)
        
        info_value = (
            f"**Спонсор:** `{data.get('sponsor')}`\n"
            f"**Победителей:** `{data.get('winner_count', 1)}`"
        )
        embed.add_field(name="", value=info_value, inline=True)
        
        # Таймер и участники
        embed.add_field(name="", value=(
            f"**Участников:** `{len(data.get('participants', []))}`\n"
            f"**Завершение:** <t:{int(datetime.strptime(data['end_time'], '%Y-%m-%d %H:%M').timestamp())}:R>"
        ), inline=True)
        embed.set_footer(text="Нажми на кнопку ниже, чтобы испытать удачу!")
        view = GiveawayUserView()

        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
    else:

        embed = discord.Embed(title="```РОЗЫГРЫШ ЗАВЕРШЕН```", color=discord.Color.from_rgb(54, 57, 63))
        embed.add_field(name="Был разыгран приз", value=f"**{data.get('prize', '---')}**", inline=False)
        
        if data and data.get("winners"):
            mentions = [f"<@{wid}>" for wid in data["winners"]]
            embed.add_field(name="Победители", value="\n".join(mentions) if mentions else "Не определены", inline=False)
        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)
        embed.set_footer(text="Следите за новыми анонсами!")
        view = None

    if message:
        await message.edit(embed=embed, view=view)
    else:
        message = await channel.send(embed=embed, view=view)
        data["fixed_message_id"] = message.id
        save_giveaway_data(data)


class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_giveaway_end.start()
        self.bot.add_view(GiveawayUserView())
        self.bot.add_view(GiveawayAdminView())

    def cog_unload(self):
        self.check_giveaway_end.cancel()

    async def setup_giveaway_panels(self):
        if not self.bot.guilds:
            print("[РОЗЫГРЫШ] Бот не находится ни на одном сервере.")
            return

        guild = self.bot.guilds[0]

        await update_user_giveaway_embed(guild)

        admin_channel = guild.get_channel(GIVEAWAY_ADMIN_CHANNEL_ID)
        if admin_channel:
            try:
                await admin_channel.purge(limit=50)
            except Exception as e:
                print(f"[РОЗЫГРЫШ] Не удалось очистить админский канал: {e}")

            admin_embed = discord.Embed(title="Панель редактирования розыгрыша", color=discord.Color.from_rgb(54, 57, 63))
            view = GiveawayAdminView()
            await admin_channel.send(embed=admin_embed, view=view)

    @tasks.loop(minutes=1)
    async def check_giveaway_end(self):
        data = load_giveaway_data()
        
        if not data or data.get("status") == "finished":
            return

        if not self.bot.guilds:
            return

        guild = self.bot.guilds[0]
        end_time_str = data.get("end_time")
        if not end_time_str:
            return

        try:
            end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M")
            
            if datetime.now() >= end_dt:
                participants = data.get("participants", [])
                winner_count = int(data.get("winner_count", 1))
                winner_ids = []
                if data.get("preselected_winners"):
                    winner_ids = data["preselected_winners"]
                elif participants:
                    actual_winners_count = min(len(participants), winner_count)
                    winner_ids = random.sample(participants, actual_winners_count)

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
                        title="Розыгрыш завершен (Авто)",
                        description=f"**Приз:** {data.get('prize')}\n**Победители:** {mentions_log}",
                        color=discord.Color.from_rgb(54, 57, 63),
                        timestamp=datetime.now(timezone.utc)
                    )

                    
                    if guild.icon:
                        log_embed.set_thumbnail(url=guild.icon.url)
                    
                    
                    log_embed.set_author(name=guild.name, icon_url=guild.icon.url if guild.icon else None)

                    await log_channel.send(embed=log_embed)

        except Exception as e:
            print(f"[ОШИБКА ТАЙМЕРА] {e}")


async def setup(bot):
    cog = GiveawayCog(bot)
    await bot.add_cog(cog)