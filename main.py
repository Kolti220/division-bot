import discord
from discord.ext import commands
import json
import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Устанавливаем интенты
intents = discord.Intents.default()
intents.message_content = True  # Чтобы бот мог читать содержимое сообщений
intents.messages = True  # Чтобы бот мог удалять сообщения

# Создаем экземпляр бота
bot = commands.Bot(command_prefix='!', intents=intents)

# Словарь для хранения ID каналов
channel_ids = []

# Словарь для хранения очков пользователей
user_points = {}

# Список ID ролей, которые могут использовать команды добавления и снятия очков и очистки сообщений
allowed_role_ids = [1365244035807318027, 1365244014395392040, 1365243619656732736]  # Замените на ваши ID ролей

def has_allowed_role(ctx):
    return any(role.id in allowed_role_ids for role in ctx.author.roles)

def load_data():
    global user_points, channel_ids
    if os.path.exists('data.json'):
        with open('data.json', 'r') as f:
            data = json.load(f)
            user_points = data.get('user_points', {})
            channel_ids = data.get('channel_ids', [])

def save_data():
    with open('data.json', 'w') as f:
        json.dump({'user_points': user_points, 'channel_ids': channel_ids}, f)

@bot.event
async def on_ready():
    load_data()  # Загружаем данные при старте бота
    print(f'Бот {bot.user} подключился!')

@bot.slash_command(name="select_channel", description="Установить канал для отчетов")
async def select_channel(ctx: discord.ApplicationContext, channel: discord.TextChannel):
    global channel_ids
    if channel.id not in channel_ids:
        channel_ids.append(channel.id)
        save_data()  # Сохраняем данные после изменения канала
        await ctx.respond(f'Канал для отчетов установлен: {channel.mention}', ephemeral=True)
    else:
        await ctx.respond("Этот канал уже добавлен.", ephemeral=True)

@bot.slash_command(name="unselect_channel", description="Удалить канал из списка отчетов")
async def unselect_channel(ctx: discord.ApplicationContext, channel: discord.TextChannel):
    global channel_ids
    if channel.id in channel_ids:
        channel_ids.remove(channel.id)
        save_data()  # Сохраняем данные после изменения канала
        await ctx.respond(f'Канал удален из списка отчетов: {channel.mention}', ephemeral=True)
    else:
        await ctx.respond("Этот канал не найден в списке отчетов.", ephemeral=True)

@bot.slash_command(name="remove_channel", description="Удалить канал из списка отчетов (устаревшая команда)")
async def remove_channel(ctx: discord.ApplicationContext, channel: discord.TextChannel):
    await unselect_channel(ctx, channel)  # Переиспользуем логику unselect_channel

@bot.slash_command(name="add", description="Добавить очки пользователю")
async def add(ctx: discord.ApplicationContext, user: discord.User, points: int, *, reason: str):
    global channel_ids
    
    if not channel_ids or not has_allowed_role(ctx):
        await ctx.respond("У вас нет прав для выполнения этой команды или каналы не установлены.", ephemeral=True)
        return 

    await ctx.defer()  # Уведомляем Discord о том, что команда обрабатывается

    user_points[user.id] = user_points.get(user.id, 0) + points
    
    embed = discord.Embed(title="Отчёт о выдаче очков", color=0x00ff00)
    embed.add_field(name="Военнослужащий", value=user.mention)
    embed.add_field(name="Получает", value=f"{points} очков.")
    embed.add_field(name="Причина", value=reason)
    embed.add_field(name="Выдал", value=ctx.author.mention)
    
    for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        if channel is not None:
            await channel.send(embed=embed)

    await ctx.respond("Очки успешно добавлены.", ephemeral=True)  # Ответ пользователю

@bot.slash_command(name="take", description="Снять очки у пользователя")
async def take(ctx: discord.ApplicationContext, user: discord.User, points: int, *, reason: str):
    global user_points
    
    if not has_allowed_role(ctx):
        await ctx.respond("У вас нет прав для выполнения этой команды.", ephemeral=True)
        return 

    await ctx.defer()  # Уведомляем Discord о том, что команда обрабатывается

    user_points[user.id] = user_points.get(user.id, 0) - points
    
    embed = discord.Embed(title="Отчёт о снятии очков", color=0x00ff00)
    embed.add_field(name="Военнослужащий", value=user.mention)
    embed.add_field(name="Лишается", value=f"{points} очков.")
    embed.add_field(name="Причина", value=reason)
    embed.add_field(name="Снял", value=ctx.author.mention)

    for channel_id in channel_ids:
        channel = bot.get_channel(channel_id)
        if channel is not None:
            await channel.send(embed=embed)

    await ctx.respond("Очки успешно сняты.", ephemeral=True)  # Ответ пользователю

@bot.slash_command(name="points", description="Количество очков у пользователя")
async def points(ctx: discord.ApplicationContext, user: discord.User):
    
    balance = user_points.get(user.id, 0)

    embed = discord.Embed(title="Отчёт о наличии очков", color=0x00ff00)
    embed.add_field(name="Военнослужащий", value=user.mention)
    embed.add_field(name="Имеет", value=f"{balance} очков.")  

    await ctx.respond(embed=embed)  # Ответ пользователю

# Команда /clear для удаления сообщений
@bot.slash_command(name="clear", description="Удалить указанное количество сообщений в канале")
async def clear(ctx: discord.ApplicationContext, amount: int):
    
    if not has_allowed_role(ctx):
        await ctx.respond("У вас нет прав для выполнения этой команды.", ephemeral=True)
        return
    
    if amount < 1 or amount > 100:
        await ctx.respond("Укажите количество от 1 до 100.", ephemeral=True)
        return

    deleted = await ctx.channel.purge(limit=amount + 1)  
    
    await ctx.respond(f"Удалено {len(deleted)-1} сообщений.", ephemeral=True)  

# Сохраняем данные при завершении работы бота.
@bot.event
async def on_disconnect():
   save_data()

if __name__ == "__main__":
   if DISCORD_TOKEN is None:
       print("Ошибка: Токен Discord не установлен.")
   else:
       try:
           bot.run(DISCORD_TOKEN)  
       except Exception as e:
           print(f"Ошибка при запуске бота: {e}")
