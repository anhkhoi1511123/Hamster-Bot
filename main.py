import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# 1. Tạo một server web nhỏ để "lừa" Koyeb rằng ứng dụng vẫn đang hoạt động
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    # Koyeb sẽ cung cấp PORT qua biến môi trường, mặc định là 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 2. Setup Bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Đã đăng nhập thành công: {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

# 3. Chạy cả 2
keep_alive()
token = os.environ.get("DISCORD_TOKEN") # Lấy token từ Environment Variables của Koyeb
bot.run(token)
