import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import asyncio

# --- PHẦN 1: TẠO SERVER WEB ĐỂ CHỐNG NGỦ TRÊN KOYEB ---
app = Flask('')
@app.route('/')
def home():
    return "Hamster Bot is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- PHẦN 2: CẤU HÌNH DISCORD BOT ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# Giao diện nút bấm chọn danh mục
class ShopCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🤖 AI Tools", style=discord.ButtonStyle.primary, custom_id="ai_tools")
    async def ai_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🤖 DANH SÁCH CÔNG CỤ AI", color=discord.Color.blue())
        embed.add_field(name="✨ ChatGPT Plus GPT-5", value="• Team: 169K/tháng\n• Chính chủ: 248K/tháng", inline=False)
        embed.add_field(name="♊ Gemini Pro", value="• 448K/năm (~37K/tháng)", inline=False)
        embed.add_field(name="🎙️ ElevenLabs", value="• 499K/3 tháng (100k credit/tháng)", inline=False)
        await interaction.response.send_message(embed=embed, view=TicketView(), ephemeral=True)

    @discord.ui.button(label="🎬 Video & Design", style=discord.ButtonStyle.success, custom_id="video_tools")
    async def video_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🎬 CÔNG CỤ VIDEO & THIẾT KẾ", color=discord.Color.green())
        embed.add_field(name="✂️ CapCut Pro", value="• 99K/tháng (Chính chủ 2-3 máy)", inline=False)
        embed.add_field(name="📽️ HeyGen Creator", value="• 399K/tháng (Gói tốt nhất)", inline=False)
        embed.add_field(name="🖌️ Canva Pro", value="• 299K/năm", inline=False)
        await interaction.response.send_message(embed=embed, view=TicketView(), ephemeral=True)

# Giao diện nút mở Ticket mua hàng
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="💳 Mở Ticket Mua Hàng", style=discord.ButtonStyle.danger, emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        # Tạo channel riêng cho khách
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(name=f'ticket-{user.name}', overwrites=overwrites)
        
        await channel.send(f"Chào {user.mention}! Cảm ơn bạn đã quan tâm sản phẩm của **Hamster Shop**. \nNgài Hamster sẽ sớm có mặt để hỗ trợ bạn thanh toán và bàn giao tài khoản nhé! 🐹✨")
        await interaction.response.send_message(f"Đã tạo Ticket thành công tại {channel.mention}!", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} đã sẵn sàng phục vụ Ngài Hamster!')

@bot.command()
async def shop(ctx):
    embed = discord.Embed(
        title="🐹 CHÀO MỪNG ĐẾN VỚI HAMSTER SHOP 🐹",
        description="Vui lòng nhấn vào danh mục bạn quan tâm bên dưới để xem chi tiết và mua hàng!",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    await ctx.send(embed=embed, view=ShopCategoryView())

# --- PHẦN 3: CHẠY BOT ---
keep_alive()
token = os.environ.get('TOKEN')
if token:
    bot.run(token)
else:
    print("LỖI: Chưa cấu hình TOKEN trong Environment Variables!")
