import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- CẤU HÌNH CƠ BẢN ---
app = Flask('')
@app.route('/')
def home(): return "Hamster Shop is Running!"

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    Thread(target=run_flask).start()

# --- LƯU TRỮ TẠM THỜI (Khi bot tắt trên Koyeb sẽ reset, nếu muốn vĩnh viễn cần Database) ---
shop_config = {
    "shop_channel_id": None,
    "bill_channel_id": None,
    "products": [] # Danh sách sản phẩm: {"name": "...", "price": "..."}
}

# --- SETUP BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='h!', intents=intents)

# --- GIAO DIỆN MUA HÀNG (DROPDOWN) ---
class ShopDropdown(discord.ui.Select):
    def __init__(self, products):
        options = []
        for p in products:
            options.append(discord.SelectOption(
                label=p['name'], 
                description=f"Giá: {p['price']}", 
                emoji="🛒"
            ))
        
        super().__init__(placeholder="Chọn sản phẩm bạn muốn mua...", options=options)

    async def callback(self, interaction: discord.Interaction):
        # Tìm thông tin sản phẩm đã chọn
        selected_product = next(p for p in shop_config["products"] if p['name'] == self.values[0])
        
        # 1. Gửi phản hồi riêng cho khách
        await interaction.response.send_message(
            f"✅ Bạn đã chọn mua: **{selected_product['name']}**\n💰 Giá: **{selected_product['price']}**\n\nVui lòng đợi Admin liên hệ hoặc tạo Ticket để thanh toán!", 
            ephemeral=True
        )

        # 2. Gửi thông báo đơn hàng (Bill) vào kênh Bill đã setup
        if shop_config["bill_channel_id"]:
            bill_channel = bot.get_channel(shop_config["bill_channel_id"])
            if bill_channel:
                embed_bill = discord.Embed(title="🧾 ĐƠN HÀNG MỚI", color=discord.Color.green())
                embed_bill.add_field(name="👤 Khách hàng", value=interaction.user.mention, inline=True)
                embed_bill.add_field(name="📦 Sản phẩm", value=selected_product['name'], inline=True)
                embed_bill.add_field(name="💵 Tổng tiền", value=selected_product['price'], inline=True)
                embed_bill.set_footer(text=f"ID Khách: {interaction.user.id}")
                await bill_channel.send(embed=embed_bill)

class ShopView(discord.ui.View):
    def __init__(self, products):
        super().__init__(timeout=None)
        self.add_item(ShopDropdown(products))

# --- CÁC LỆNH SETUP (h!) ---

@bot.command()
@commands.has_permissions(administrator=True)
async def setshop(ctx, channel: discord.TextChannel):
    """Thiết lập kênh hiển thị menu bán hàng"""
    shop_config["shop_channel_id"] = channel.id
    await ctx.send(f"✅ Đã thiết lập kênh Shop tại: {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def setbill(ctx, channel: discord.TextChannel):
    """Thiết lập kênh gửi hóa đơn (bill)"""
    shop_config["bill_channel_id"] = channel.id
    await ctx.send(f"✅ Đã thiết lập kênh Bill tại: {channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def lendon(ctx, name: str, price: str):
    """Thêm sản phẩm mới và cập nhật Menu Shop"""
    if not shop_config["shop_channel_id"]:
        return await ctx.send("❌ Bạn chưa set kênh shop! Hãy dùng `h!setshop #tên-kênh` trước.")
    
    # Thêm vào danh sách sản phẩm
    shop_config["products"].append({"name": name, "price": price})
    
    # Gửi/Cập nhật Menu tại kênh Shop
    shop_channel = bot.get_channel(shop_config["shop_channel_id"])
    
    embed = discord.Embed(
        title="🍃 HAMSTER STORE MENU 🍃",
        description="Nhấn vào thanh bên dưới để chọn sản phẩm bạn muốn mua!",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    
    # Hiển thị danh sách sản phẩm hiện có trong Embed
    product_list = ""
    for p in shop_config["products"]:
        product_list += f"• **{p['name']}**: {p['price']}\n"
    embed.add_field(name="📦 Danh sách sản phẩm:", value=product_list or "Đang cập nhật...", inline=False)
    
    await shop_channel.send(embed=embed, view=ShopView(shop_config["products"]))
    await ctx.send(f"✅ Đã lên đơn thành công sản phẩm: **{name}**")

@bot.event
async def on_ready():
    print(f'Đã sẵn sàng: {bot.user}')

keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN"))
