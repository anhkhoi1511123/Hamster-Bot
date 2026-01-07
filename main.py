import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- PHẦN 1: THIẾT LẬP SERVER WEB ĐỂ GIỮ BOT ONLINE (KEEP-ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Hamster Bot is Online!"

def run_flask():
    # Koyeb yêu cầu ứng dụng chạy trên Port do họ cung cấp (mặc định 8080)
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # Chạy server Flask trong một luồng (thread) riêng để không làm gián đoạn bot
    t = Thread(target=run_flask)
    t.start()

# --- PHẦN 2: CẤU HÌNH BOT DISCORD ---
# Cấp quyền cho bot (Intents)
intents = discord.Intents.default()
intents.message_content = True  # Cho phép bot đọc nội dung tin nhắn

# Khởi tạo bot với tiền tố lệnh là dấu chấm cảm (!)
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'------------------------------------')
    print(f'Đã đăng nhập thành công: {bot.user}')
    print(f'ID Bot: {bot.user.id}')
    print(f'------------------------------------')

# Các lệnh của bot
@bot.command()
async def ping(ctx):
    await ctx.send(f'🏓 Pong! Độ trễ: {round(bot.latency * 1000)}ms')

@bot.command()
async def hello(ctx):
    await ctx.send('Chào bạn! Hamster Bot đã sẵn sàng phục vụ! 🐹')

# --- PHẦN 3: KÍCH HOẠT VÀ CHẠY BOT ---
if __name__ == "__main__":
    # 1. Khởi động server web
    keep_alive()
    
    # 2. Lấy Token từ Environment Variables (Biến môi trường) trên Koyeb
    token = os.environ.get("DISCORD_TOKEN")
    
    # 3. Chạy bot
    if token:
        try:
            bot.run(token)
        except Exception as e:
            print(f"Lỗi khi khởi động bot: {e}")
    else:
        print("LỖI: Không tìm thấy DISCORD_TOKEN. Hãy kiểm tra lại Settings trên Koyeb!")
