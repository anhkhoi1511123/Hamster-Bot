import discord
from discord.ext import commands
import os
import random
from datetime import datetime
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# ==========================================
# 1. KẾT NỐI DATABASE (Sử dụng biến môi trường)
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
client_db = MongoClient(MONGO_URI)
db = client_db["hamster_bot_data"]
users_col = db["users"]
settings_col = db["settings"]

# ==========================================
# 2. WEB SERVER CHO KOYEB (PORT TỰ ĐỘNG)
# ==========================================
app = Flask('')

@app.route('/')
def home(): return "Hamster Bot is Online!"

def run():
    # Koyeb cung cấp cổng qua biến PORT, mặc định là 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

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
    print(f'✅ Bot sẵn sàng: {bot.user.name}')

# ==========================================
# 4. HỆ THỐNG LỆNH
# ==========================================

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🐹 MENU HAMSTER BOT", color=0xffeaa7)
    embed.add_field(name="🛠 Quản lý", value="`setshop`, `removeshop`, `setorder`, `xoasp`, `setbill`, `removebill`", inline=False)
    embed.add_field(name="💰 Kinh tế", value="`work`, `daily`, `bal`, `buy`, `inv`", inline=False)
    await ctx.send(embed=embed)

# --- QUẢN LÝ SHOP ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setshop(ctx, channel: discord.TextChannel = None):
    target = channel or ctx.channel
    settings_col.update_one({"_id": "shop_config"}, {"$set": {"channel_id": target.id}}, upsert=True)
    await ctx.send(f"✅ Đã đặt {target.mention} làm kênh bán hàng.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removeshop(ctx):
    settings_col.delete_one({"_id": "shop_config"})
    await ctx.send("🗑 Đã xóa cấu hình Shop.")

@bot.command()
@commands.has_permissions(administrator=True)
async def setorder(ctx, name: str, price: str, channel: discord.TextChannel = None, role: discord.Role = None):
    # Lấy kênh shop đã set hoặc dùng kênh hiện tại
    config = settings_col.find_one({"_id": "shop_config"})
    target_channel = channel or (bot.get_channel(config["channel_id"]) if config else ctx.channel)
    role_mention = role.mention if role else ""

    embed = discord.Embed(
        title="Tiệm Tạp Hóa Nhà Hamster",
        description=f"✨ **Sản phẩm:** {name}\n💰 **Giá:** `{price}`\n\n*(Dùng h!buy để mua)*",
        color=0xFFB6C1
    )
    
    # Lưu thông tin bán hàng hiện tại để người dùng có thể h!buy
    settings_col.update_one({"_id": "current_sale"}, {"$set": {"name": name, "price": price}}, upsert=True)

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
        settings_col.update_one({"_id": "shop_menu"}, {"$set": {"message_id": new_msg.id, "channel_id": target_channel.id}}, upsert=True)

    await ctx.send(f"✅ Đã lên đơn thành công sản phẩm: **{name}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def xoasp(ctx):
    menu_data = settings_col.find_one({"_id": "shop_menu"})
    if menu_data:
        try:
            ch = bot.get_channel(menu_data["channel_id"])
            msg = await ch.fetch_message(menu_data["message_id"])
            await msg.edit(content="", embed=discord.Embed(title="Tiệm Tạp Hóa Nhà Hamster", description="Hiện tại hết hàng.", color=0xcccccc))
            settings_col.delete_one({"_id": "current_sale"})
            await ctx.send("✅ Đã dọn kệ hàng.")
        except: await ctx.send("❌ Không tìm thấy menu.")

# --- HÓA ĐƠN ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setbill(ctx, channel: discord.TextChannel = None):
    target = channel or ctx.channel
    settings_col.update_one({"_id": "bill_config"}, {"$set": {"channel_id": target.id}}, upsert=True)
    await ctx.send(f"📋 Hóa đơn sẽ được gửi vào {target.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def removebill(ctx):
    settings_col.delete_one({"_id": "bill_config"})
    await ctx.send("🗑 Đã tắt tính năng hóa đơn.")

# --- KINH TẾ ---
@bot.command()
async def work(ctx):
    money = random.randint(50, 200)
    users_col.update_one({"_id": ctx.author.id}, {"$inc": {"balance": money}}, upsert=True)
    await ctx.send(f"🐹 {ctx.author.name} đã làm việc và nhận `{money} xu`!")

@bot.command()
async def bal(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(f"💰 Số dư: `{user['balance']} xu`")

@bot.command()
async def buy(ctx):
    sale = settings_col.find_one({"_id": "current_sale"})
    if not sale: return await ctx.send("❌ Shop đang hết hàng.")
    
    user = get_user(ctx.author.id)
    try:
        price_val = int(''.join(filter(str.isdigit, sale['price'])))
    except: price_val = 0

    if user['balance'] < price_val:
        return await ctx.send(f"❌ Bạn thiếu `{price_val - user['balance']} xu`.")

    users_col.update_one({"_id": ctx.author.id}, {"$inc": {"balance": -price_val}, "$push": {"inventory": sale['name']}})
    await ctx.send(f"🎉 Bạn đã mua **{sale['name']}** thành công!")

    # Gửi hóa đơn về kênh bill
    bill_cfg = settings_col.find_one({"_id": "bill_config"})
    if bill_cfg:
        bill_ch = bot.get_channel(bill_cfg['channel_id'])
        if bill_ch:
            await bill_ch.send(f"🧾 **HÓA ĐƠN:** {ctx.author.mention} đã mua `{sale['name']}` giá `{sale['price']}`")

@bot.command()
async def inv(ctx):
    user = get_user(ctx.author.id)
    items = ", ".join(user['inventory']) if user['inventory'] else "Trống"
    await ctx.send(f"🎒 Túi đồ của bạn: {items}")

# --- CHẠY ---
keep_alive()
bot.run(os.getenv("BOT_TOKEN"))
