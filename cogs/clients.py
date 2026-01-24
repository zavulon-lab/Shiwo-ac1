
import discord
from discord.ext import commands
import asyncio


class ClientSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.select(
    placeholder="Выбери интересующий клиент...",
    min_values=1,
    max_values=1,
    options=[
        discord.SelectOption(
            label="Nightfall",
            value="nightfall",
            emoji=discord.PartialEmoji(
                name="logo_footer",
                id=1462182809472077938 
            )
        ),
        discord.SelectOption(
            label="Astra",
            value="astra",
            emoji=discord.PartialEmoji(
                name="astra",
                id=1462182689896403095
            )
        ),
        discord.SelectOption(
            label="Leet",
            value="leet",
            emoji=discord.PartialEmoji(
                name="leet",
                id=1462184487692533936
            )
        ),
        discord.SelectOption(
            label="Unicore",
            value="unicore",
            emoji=discord.PartialEmoji(
                name="unicore",
                id=1462193986969272595
            )
        ),
        discord.SelectOption(
            label="Vanish",
            value="vanish",
            emoji=discord.PartialEmoji(
                name="vanish",
                id=1462193887366877434
            )
        ),
        discord.SelectOption(
            label="Skript-GG",
            value="skriptgg",
            emoji=discord.PartialEmoji(
                name="skriptgg",
                id=1462194037581942981
            )
        ),
    ]
)

    async def client_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        await interaction.response.defer(ephemeral=True)

        if select.values[0] == "nightfall":
            embeds = []

            # Страница 1
            embeds.append(
                discord.Embed(
                    title="Nightfall — Проверка через Process Hacker",
                    description=(
                        "**Process Hacker**\n"
                        "• Открываем **Process Hacker**\n"
                        "• Находим браузер пользователя\n"
                        "• Дважды нажимаем **ЛКМ** по процессу\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            # Страница 2 — картинка
            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462165601916293330/64573893-09FD-481F-A85E-F4E0AE19C71D.png?ex=696d3355&is=696be1d5&hm=abd9615885527ca378b5f2f2a49a796f4d49e3a77f1b42798d9abb2bfccd35ca&"
                )
            )

            # Страница 3
            embeds.append(
                discord.Embed(
                    description=(
                        "• Переходим во вкладку **Filter**\n"
                        "• Выбираем **Contains (case insensitive)**\n"
                        "• Вводим: `nightfall`\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            # Страница 4 — картинка
            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462165601567903775/95394B17-6D40-4B22-B352-1783C4A3DFAF.png?ex=696d3355&is=696be1d5&hm=b2cd0e2ada5d8349a22849c5b3d7464c9488af7bc20ddf5da09b04befe7c9a48&"
                )
            )

            # Страница 5 — финальная
            embeds.append(
                discord.Embed(
                    description=(
                        "**Поиск входа в профиль**\n"
                        "• Анализируем обращения к профилю пользователя\n\n"
                        "**Journal Tool**\n"
                        "• Ставим галки **Delete** и **Deleted**\n"
                        "• В поиске вводим `.exe`\n"
                        "• Внимательно просматриваем удалённые файлы\n\n"
                        "**Journal Trace**\n"
                        "• Проверяем события:\n"
                        "  – Data truncation\n"
                        "  – Close File delete\n"
                        "  – Close Rename: new name\n\n"
                        "Сверяйте время и названия файлов"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=discord.utils.utcnow()
                )
            )

            embeds[-1].set_footer(
                text="Shiwo ac • nightfall",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            await interaction.followup.send(embeds=embeds, ephemeral=True)
            return

        if select.values[0] == "astra":
            embeds = []

            embeds.append(
                discord.Embed(
                    title="Astra — Проверка через Process Hacker",
                    description=(
                        "**Process Hacker**\n"
                        "• Открываем **Process Hacker**\n"
                        "• Находим браузер пользователя\n"
                        "• Дважды нажимаем **ЛКМ** по процессу\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462203833013895415/A8CEDD88-3EED-4F60-BE58-BEA87D7A1A70.png?ex=696d56f0&is=696c0570&hm=e93281a0ebc4bf763341c4426dbeed229f593d609a3c318e8952d3ec26f31a4f&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "• Переходим во вкладку **Filter**\n"
                        "• Выбираем **Contains (case insensitive)**\n"
                        "• Вводим: `up-game`\n\n"
                        "• Ищем заход в профиль пользователя\n"
                        "• Обращаем внимание на процессы **lsass** и **dnscache**\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462203832531423383/99A16DF6-D45E-4380-B2BA-CF379F5F40BE.png?ex=696d56f0&is=696c0570&hm=e8b74cea5fded48da7cb5c3d1fa6072b219d7cc99b06f4b991c79e5c93ab539a&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "• В строке поиска вводим: `astra.rip`\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462203833303433420/FA54AC14-6670-456D-9C22-0BBCEEB48E9C.png?ex=696d56f0&is=696c0570&hm=b742decd6d658e286b4d232849b8d66e29bdaed4916fd588b0690c38a6a67e45&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Journal Tool**\n"
                        "• Ставим галочку **Delete**\n"
                        "• Включаем **Deleted**\n"
                        "• В поиске вводим: `.exe`\n"
                        "• Внимательно просматриваем удалённые файлы\n\n"
                        "**Journal Trace**\n"
                        "• Копируем имя подозрительного `.exe`\n"
                        "• Вставляем в **Journal Trace**\n"
                        "• Анализируем:\n"
                        "  – Время событий\n"
                        "  – `Data truncation`\n"
                        "  – `Close File delete`\n"
                        "  – `Close Rename: new name`\n\n"
                        "Сопоставляйте время активности с запуском клиента"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=discord.utils.utcnow()
                )
            )

            embeds[-1].set_footer(
                text="Shiwo ac • astra",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            await interaction.followup.send(
                embeds=embeds,
                ephemeral=True
            )
            return


        if select.values[0] == "leet":
            embeds = []

            embeds.append(
                discord.Embed(
                    title="Leet / 1337 — Проверка через Process Hacker",
                    description=(
                        "**Process Hacker**\n"
                        "• Открываем **Process Hacker**\n"
                        "• Находим браузер пользователя\n"
                        "• Дважды нажимаем **ЛКМ** по процессу\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://media.discordapp.net/attachments/1462165491278938204/1462204765076197607/5205DAF9-8A67-484D-8A57-DFEDC8973B61.png?ex=696d57ce&is=696c064e&hm=379b567f1799b82e99e44ccf21e45a0c41c179179a6cbba3068967510b2ab456&=&format=webp&quality=lossless&width=678&height=858"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "• Переходим во вкладку **Filter**\n"
                        "• Выбираем **Contains (case insensitive)**\n"
                        "• Вводим: `leet` или `1337`\n\n"
                        "• Ищем заход в профиль пользователя\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462204764707229931/1BA6EDEF-13FF-4988-96C7-104A6BD9CBF3.png?ex=696d57ce&is=696c064e&hm=b37e8aa484b2b231cf26834adb221e3a8f0c31256fe3d1805d563c081d055c67&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "• Проверяем вход в профиль клиента\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://media.discordapp.net/attachments/1462165491278938204/1462204765604937912/C1A37644-79E7-474C-9A44-AFAEF53625F4.png?ex=696d57ce&is=696c064e&hm=fd99156aca58a761e4d733fc15046d5820906d04d31d281751ccd3ea727b2ed2&=&format=webp&quality=lossless&width=728&height=752"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Journal Tool**\n"
                        "• Ставим галочку **Delete**\n"
                        "• Включаем **Deleted**\n"
                        "• В поиске вводим: `.exe`\n"
                        "• Внимательно просматриваем удалённые файлы\n\n"
                        "**Journal Trace**\n"
                        "• Копируем имя подозрительного `.exe`\n"
                        "• Вставляем в **Journal Trace**\n"
                        "• Анализируем:\n"
                        "  – Время событий\n"
                        "  – `Data truncation`\n"
                        "  – `Close File delete`\n"
                        "  – `Close Rename: new name`\n\n"
                        "Сопоставляйте время активности с запуском клиента"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=discord.utils.utcnow()
                )
            )

            embeds[-1].set_footer(
                text="Shiwo ac • leet",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            await interaction.followup.send(
                embeds=embeds,
                ephemeral=True
            )
            return

        if select.values[0] == "unicore":
            embeds = []

            embeds.append(
                discord.Embed(
                    title="Unicore — Проверка через Process Hacker",
                    description=(
                        "**Process Hacker**\n"
                        "• Находим браузер пользователя\n"
                        "• Дважды нажимаем ЛКМ по процессу\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205070832828588/photo_2026-01-17_17-20-35.jpg?ex=696d5817&is=696c0697&hm=aa93c67afd9ce837a2fee117ba31eb3768576101e1f475b701ac7c4a1dbaf473&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "• Нажимаем **Filter** → **Contains (case insensitive)**\n"
                        "• Вводим: `unicore`\n"
                        "• Ищем заход в профиль\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205071298138112/photo_2026-01-17_17-20-38.jpg?ex=696d5817&is=696c0697&hm=38b517d91529c8184c19595a248cee597f7273f1d83a5643dc551248291a4a8c&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Journal Trace**\n"
                        "• Открываем Journal Trace\n"
                        "• Ищем события, связанные с Unicore\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205071705116803/photo_2026-01-17_17-20-42.jpg?ex=696d5817&is=696c0697&hm=222f172484039697fda4fd21f7a8133ba0152b00da053bf1bd955d1aa88970cd&"
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205072070152214/photo_2026-01-17_17-20-46.jpg?ex=696d5817&is=696c0697&hm=3d4aacf24a9394cf982914d857ff522486dcef1cddd5e3739f2ff5ffd9805b0c&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**%programdata% (только для Epic Games)**\n"
                        "• Проверяем папку `Epic`\n"
                        "• Там должно быть **4 файла**\n\n"
                        "**Journal Tool**\n"
                        "• Ставим галочку **Delete**\n"
                        "• Включаем **Deleted**\n"
                        "• В поиске вводим: `.exe`\n"
                        "• Внимательно смотрим удалённые файлы\n\n"
                        "**Journal Trace (анализ)**\n"
                        "• Копируем название файла, который считаем “unicore”\n"
                        "• Вставляем в Journal Trace\n"
                        "• Обращаем внимание на:\n"
                        "  – Время событий\n"
                        "  – `Data truncation`\n"
                        "  – `Close File delete`\n"
                        "  – `Close Rename: new name`\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=discord.utils.utcnow()
                )
            )

            embeds[-1].set_footer(
                text="Shiwo ac • unicore",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            await interaction.followup.send(
                embeds=embeds,
                ephemeral=True
            )
            return
        if select.values[0] == "vanish":
            embeds = []

            embeds.append(
                discord.Embed(
                    title="Vanish — Проверка через Process Hacker",
                    description=(
                        "**Process Hacker**\n"
                        "• Находим браузер пользователя\n"
                        "• Дважды нажимаем ЛКМ по процессу\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205374861148305/photo_2026-01-17_17-28-37.jpg?ex=696d585f&is=696c06df&hm=754772a9e903fa7a53e1ff1ecc724c12aea4e4392b0037996d88dbdc43b1b6cd&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "• Нажимаем **Filter** → **Contains (case insensitive)**\n"
                        "• Вводим: `vanish`\n"
                        "• Ищем заход в профиль\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205375309680876/photo_2026-01-17_17-28-45.jpg?ex=696d585f&is=696c06df&hm=960455f6a68bfa8141501d5dfa5cb58cfd42cc4467737b57a1869a674f390188&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Journal Tool**\n"
                        "• Включаем **Deleted**\n"
                        "• В поиске вводим: `.exe`\n"
                        "• Внимательно смотрим файлы, которые были в папке **Загрузки** и удалены сегодня\n"
                        "• Vanish часто называется как **дефолтное приложение**\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Journal Trace**\n"
                        "• Копируем название файла, который считаем «vanish»\n"
                        "• Вставляем в Journal Trace\n"
                        "• Анализируем:\n"
                        "  – Время событий\n"
                        "  – `Data truncation`\n"
                        "  – `Close File delete`\n"
                        "  – `Close Rename: new name`\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=discord.utils.utcnow()
                )
            )

            embeds[-1].set_footer(
                text="Shiwo ac • vanish",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            await interaction.followup.send(
                embeds=embeds,
                ephemeral=True
            )
            return
        if select.values[0] == "skriptgg":
            embeds = []

            embeds.append(
                discord.Embed(
                    title="Skript-GG — Проверка через Process Hacker",
                    description=(
                        "**Безопасность Windows**\n"
                        "• Открываем **Безопасность Windows**\n"
                        "• Переходим в раздел **Журнал событий**\n"
                        "• Проверяем подозрительные действия\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://media.discordapp.net/attachments/1462165491278938204/1462205522420695304/BDC20586-F71D-4593-9F3B-E342CE3A5522.png?ex=696d5883&is=696c0703&hm=cb26af3558dcbf03a90505cee15c668084333a997cbcf6147f1d122a34538e2d&=&format=webp&quality=lossless&width=533&height=911"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Process Hacker**\n"
                        "• Находим браузер пользователя\n"
                        "• Дважды нажимаем ЛКМ по процессу\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://media.discordapp.net/attachments/1462165491278938204/1462205521573707838/34BF2D5B-D45C-46E7-99BB-84F7473BCE9E.png?ex=696d5882&is=696c0702&hm=438d91d21cbf77cb3cc36de83af706d12a9208c876a8db50712b390d2615b26d&=&format=webp&quality=lossless&width=663&height=858"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "• Нажимаем **Filter** → **Contains (case insensitive)**\n"
                        "• Вводим: `skript.gg`\n"
                        "• Ищем заход в профиль\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205521963520009/4917D985-58AD-44C7-84F6-C3B8163C9792.png?ex=696d5882&is=696c0702&hm=c526413a8180a1ddaedc4bf3a736203e897dda14bd5d7d11ae906b99a3489750&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Journal Tool**\n"
                        "• Ставим галочку **Delete**\n"
                        "• Включаем **Deleted**\n"
                        "• В поиске вводим: `.exe`\n"
                        "• Внимательно смотрим файлы\n"
                    ),
                    color=discord.Color.from_rgb(54, 57, 63)
                )
            )

            embeds.append(
                discord.Embed().set_image(
                    url="https://cdn.discordapp.com/attachments/1462165491278938204/1462205522915627130/FE4350D9-FECE-4AB8-A582-17685EFC336D.png?ex=696d5883&is=696c0703&hm=687b2a3316a69773166899a97516788c10d15d9f44d228b75607b859ac22858c&"
                )
            )

            embeds.append(
                discord.Embed(
                    description=(
                        "**Journal Trace**\n"
                        "• Копируем название файла, который считаем «skript.gg»\n"
                        "• Вставляем в Journal Trace\n"
                        "• Анализируем:\n"
                        "  – Время событий\n"
                        "  – `Data truncation`\n"
                        "  – `Close File delete`\n"
                        "  – `Close Rename: new name`\n                    "
                    ),
                    color=discord.Color.from_rgb(54, 57, 63),
                    timestamp=discord.utils.utcnow()
                )
            )

            embeds[-1].set_footer(
                text="Shiwo ac • skriptgg",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )

            await interaction.followup.send(
                embeds=embeds,
                ephemeral=True
            )
            return
        
class ClientsPanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.target_channel_id = 1462154123297427496 

    async def get_target_channel(self) -> discord.TextChannel | None:
        try:
            channel = await self.bot.fetch_channel(self.target_channel_id)
            return channel if isinstance(channel, discord.TextChannel) else None
        except Exception as e:
            print(f"[ClientsPanel] Ошибка получения канала {self.target_channel_id}: {e}")
            return None

    async def delete_previous_message(self, channel: discord.TextChannel):
        """Удаляет предыдущее сообщение панели по футеру"""
        try:
            async for message in channel.history(limit=10):
                if message.author == self.bot.user and message.embeds:
                    embed = message.embeds[0]
                    if embed.footer and "Shiwo ac • faq" in embed.footer.text:
                        await message.delete()
                        break
        except Exception as e:
            print(f"[Clients] Ошибка при удалении старой панели: {e}")

    async def send_new_panel(self, channel: discord.TextChannel):
        embed = discord.Embed(
            title="Возможно интересующие вас вопросы",
            description=(
                "Выбери интересующую тему ниже\n\n"
                "Все решения проверены на актуальность и безопасность.\n"
                "Приятного использования!"
            ),
            color=discord.Color.from_rgb(54, 57, 63)
        )

        if channel.guild.icon:
            embed.set_thumbnail(url=channel.guild.icon.url)

        embed.set_footer(text="Shiwo ac • faq")

        view = ClientSelectView()
        try:
            message = await channel.send(embed=embed, view=view)
            return message
        except Exception as e:
            print(f"[Clients] Ошибка при отправке панели: {e}")
            return None

    @commands.Cog.listener()
    async def on_ready(self):
        await asyncio.sleep(5) 
        channel = await self.get_target_channel()
        if not channel:
            print(f"[ClientsPanel] Канал {self.target_channel_id} не найден или нет доступа!")
            return

        await self.delete_previous_message(channel)
        await self.send_new_panel(channel)


async def setup(bot: commands.Bot):
    await bot.add_cog(ClientsPanelCog(bot))