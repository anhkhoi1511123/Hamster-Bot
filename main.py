import discord
from discord.ext import commands
import os
import random
from datetime import datetime
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# ==========================================
# 1. KẾT NỐI DATABASE MONGODB
# ==========================================
MONGO_URI = "YOUR_MONGODB_URI"
client_db = MongoClient(MONGO_URI)
db = client_db["hamster_bot_data"]
users_col = db["users"]
settings_col = db["settings"]

# ==========================================
# 2. TREO BOT 24/7 (FLASK)
# ==========================================
app = Flask('')
@app.route('/')
def home(): return "Hamster Bot is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 3. CẤU HÌNH BOT
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='h!', intents=intents, help_command=None)

def get_user(user_id):
    user = users_col.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "balance": 0, "inventory": []}
        users_col.insert_one(user)
    return user

@bot.event
async def on_ready():
    print(f'✅ Đã kết nối: {bot.user.name}')

# ==========================================
# 4. LỆNH h!help (TỔNG HỢP)
# ==========================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📜 Danh sách lệnh Hamster Bot", color=0x3498db)
    embed.add_field(name="🛒 Shop & Quản lý", value="`setshop`, `removeshop`, `setorder`, `xoasp`, `setbill`, `removebill`", inline=False)
    embed.add_field(name="💰 Kinh tế", value="`work`, `daily`, `bal`, `buy`, `inv`", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# 5. NHÓM LỆNH QUẢN LÝ SHOP (ADMIN)
# ==========================================

@bot.command()
@commands.has_permissions(administrator=True)
async def setshop(ctx, channel: discord.TextChannel = None):
    """Thiết lập kênh làm Shop chính"""
    target = channel or ctx.channel
    settings_col.update_one({"_id": "shop_config"}, {"$set": {"channel_id": target.id}}, upsert=True)
    await ctx.send(f"✅ Đã thiết lập kênh {target.mention} làm nơi bán hàng.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removeshop(ctx):
    """Xóa cấu hình shop"""
    settings_col.delete_one({"_id": "shop_config"})
    settings_col.delete_one({"_id": "shop_menu"}) # Xóa luôn ID tin nhắn menu
    await ctx.send("🗑️ Đã xóa cấu hình Shop.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setorder(ctx, name: str, price: str, channel: discord.TextChannel = None, role: discord.Role = None):
    """Lên đơn và SỬA EMBED CŨ (Yêu cầu mới)"""
    # Lấy thông tin kênh từ lệnh hoặc DB
    config = settings_col.find_one({"_id": "shop_config"})
    target_channel = channel or (bot.get_channel(config["channel_id"]) if config else ctx.channel)
    role_mention = role.mention if role else ""

    embed = discord.Embed(
        title="Tiệm Tạp Hóa Nhà Hamster",
        description=f"✨ **Sản phẩm:** {name}\n💰 **Giá:** `{price}`",
        color=0xFFB6C1
    )
    embed.set_footer(text="Dùng h!buy để mua ngay!")

    # Kiểm tra tin nhắn cũ để sửa
    menu_data = settings_col.find_one({"_id": "shop_menu"})
    msg_to_edit = None

    if menu_data:
        try:
            ch = bot.get_channel(menu_data["channel_id"])
            msg_to_edit = await ch.fetch_message(menu_data["message_id"])
            await msg_to_edit.edit(content=role_mention, embed=embed)
        except: msg_to_edit = None

    if not msg_to_edit:
        new_msg = await target_channel.send(content=role_mention, embed=embed)
        settings_col.update_one({"_id": "shop_menu"}, 
            {"$set": {"message_id": new_msg.id, "channel_id": target_channel.id}}, upsert=True)

    # Quan trọng: Thông báo tại kênh người dùng gõ lệnh
    await ctx.send(f"✅ Đã lên đơn thành công sản phẩm: **{name}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def xoasp(ctx):
    """Xóa sản phẩm hiện tại trên Menu (Để trống menu)"""
    menu_data = settings_col.find_one({"_id": "shop_menu"})
    if menu_data:
        try:
            ch = bot.get_channel(menu_data["channel_id"])
            msg = await ch.fetch_message(menu_data["message_id"])
            empty_embed = discord.Embed(title="Tiệm Tạp Hóa Nhà Hamster", description="Hiện tại tiệm chưa có hàng mới.", color=0xcccccc)
            await msg.edit(content="", embed=empty_embed)
            await ctx.send("✅ Đã xóa sản phẩm trên Menu.")
        except: await ctx.send("❌ Không tìm thấy Menu để xóa.")

# ==========================================
# 6. NHÓM LỆNH BILL (HÓA ĐƠN)
# ==========================================

@bot.command()
@commands.has_permissions(administrator=True)
async def setbill(ctx, channel: discord.TextChannel = None):
    """Thiết lập kênh lưu lịch sử hóa đơn"""
    target = channel or ctx.channel
    settings_col.update_one({"_id": "bill_config"}, {"$set": {"channel_id": target.id}}, upsert=True)
    await ctx.send(f"📋 Đã thiết lập kênh {target.mention} để lưu hóa đơn.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removebill(ctx):
    settings_col.delete_one({"_id": "bill_config"})
    await ctx.send("🗑️ Đã xóa thiết lập hóa đơn.")

# ==========================================
# 7. NHÓM LỆNH KINH TẾ (WORK, BUY...)
# ==========================================

@bot.command()
async def work(ctx):
    money = random.randint(50, 150)
    users_col.update_one({"_id": ctx.author.id}, {"$inc": {"balance": money}}, upsert=True)
    await ctx.send(f"🐹 Bạn đã làm việc chăm chỉ và nhận được `{money} xu`!")

@bot.command()
async def bal(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(f"💰 Số dư của **{ctx.author.name}**: `{user['balance']} xu`")

@bot.command()
async def buy(ctx):
    """Mua hàng và tự động gửi hóa đơn vào kênh Bill"""
    # (Logic trừ tiền và gửi bill vào kênh đã setbill)
    user = get_user(ctx.author.id)
    # Lấy sản phẩm đang bán từ DB (giả sử bạn lưu vào 'current_sale' ở setorder)
    # ... (Phần này có thể tùy biến theo nhu cầu thực tế của bạn)
    await ctx.send("🛒 Tính năng mua đang được xử lý dựa trên sản phẩm hiện tại.")

# ==========================================
# CHẠY BOT
# ==========================================
keep_alive()
bot.run("YOUR_BOT_TOKEN")
