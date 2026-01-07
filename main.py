import discord
from discord.ext import commands
from discord import ui # Dùng cho Modal và Dropdown
import os
import random
from flask import Flask
from threading import Thread
from pymongo import MongoClient

# ==========================================
# 1. KẾT NỐI DATABASE & KOYEB
# ==========================================
MONGO_URI = os.getenv("MONGO_URI")
client_db = MongoClient(MONGO_URI)
db = client_db["hamster_bot_v3"]
users_col = db["users"]
settings_col = db["settings"]
items_col = db["shop_items"]

app = Flask('')
@app.route('/')
def home(): return "Hamster Bot Modal Edition is Online!"
def run(): port = int(os.environ.get("PORT", 8080)); app.run(host='0.0.0.0', port=port)
def keep_alive(): t = Thread(target=run); t.start()

# ==========================================
# 2. CẤU HÌNH BOT
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

# ==========================================
# 3. MODAL: BIỂU MẪU GHI CHÚ
# ==========================================
class OrderModal(ui.Modal, title='Thông Tin Đơn Hàng'):
    # Trường nhập liệu ghi chú
    note = ui.TextInput(
        label='Ghi chú cho người cày thuê',
        style=discord.TextStyle.paragraph,
        placeholder='Nhập tên tài khoản, mật khẩu hoặc yêu cầu riêng tại đây...',
        required=True,
        max_length=500
    )

    def __init__(self, item_name, price):
        super().__init__()
        self.item_name = item_name
        self.price = price

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        user_data = get_user(user_id)

        # Kiểm tra lại tiền một lần nữa
        if user_data['balance'] < self.price:
            return await interaction.response.send_message(f"❌ Bạn không đủ tiền để hoàn tất đơn hàng!", ephemeral=True)

        # Trừ tiền và lưu inventory
        users_col.update_one({"_id": user_id}, {"$inc": {"balance": -self.price}, "$push": {"inventory": self.item_name}})

        # Gửi thông báo thành công cho khách
        await interaction.response.send_message(f"🎉 Đã gửi đơn hàng thành công! Vui lòng chờ người cày liên hệ.", ephemeral=True)

        # --- GỬI BILL VỀ KÊNH HÓA ĐƠN (Theo ảnh mẫu) ---
        bill_cfg = settings_col.find_one({"_id": "bill_config"})
        if bill_cfg:
            bill_ch = bot.get_channel(bill_cfg['channel_id'])
            if bill_ch:
                # Tạo Embed giống ảnh mẫu bạn gửi
                bill_embed = discord.Embed(
                    title="📦 ĐƠN HÀNG",
                    description=(
                        f"┃ 👤 **Người Mua Hàng:**\n{interaction.user.mention}\n"
                        f"┃ 📦 **Món Hàng:**\n`{self.item_name}`\n"
                        f"┃ 🍃 **Trạng Thái:**\n`🔄 Đang làm`\n"
                        f"┃ 💸 **Price/Giá:**\n`{self.price:,.0f} xu`\n\n"
                        f"**📝 Ghi chú khách:**\n{self.note.value}"
                    ),
                    color=0xFFD700 # Màu vàng giống biểu tượng hộp quà
                )
                bill_embed.set_author(name="Mây Sì To", icon_url=bot.user.avatar.url if bot.user.avatar else None)
                await bill_ch.send(embed=bill_embed)

# ==========================================
# 4. DROPDOWN MUA HÀNG
# ==========================================
class ShopDropdown(ui.Select):
    def __init__(self, items_list):
        options = [discord.SelectOption(label=i['name'], description=f"Giá: {i['price']} xu", emoji="🛒", value=i['name']) for i in items_list]
        if not options: options = [discord.SelectOption(label="Hết hàng", value="none")]
        super().__init__(placeholder="🔻 Chọn dịch vụ cày thuê tại đây...", options=options, disabled=not items_list)

    async def callback(self, interaction: discord.Interaction):
        item_name = self.values[0]
        if item_name == "none": return
        
        item_data = items_col.find_one({"name": item_name})
        if not item_data: return await interaction.response.send_message("Sản phẩm không tồn tại.", ephemeral=True)
        
        # Kiểm tra tiền trước khi hiện Modal
        user_data = get_user(interaction.user.id)
        if user_data['balance'] < item_data['price']:
            return await interaction.response.send_message(f"❌ Bạn cần `{item_data['price']} xu` để mua món này.", ephemeral=True)

        # Hiện Modal biểu mẫu
        await interaction.response.send_modal(OrderModal(item_name, item_data['price']))

class ShopView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        items_list = list(items_col.find({}))
        self.add_item(ShopDropdown(items_list))

# ==========================================
# 5. LỆNH QUẢN LÝ
# ==========================================

@bot.command()
@commands.has_permissions(administrator=True)
async def setorder(ctx, name: str, price: int, channel: discord.TextChannel = None, role: discord.Role = None):
    items_col.update_one({"name": name}, {"$set": {"price": price}}, upsert=True)
    config = settings_col.find_one({"_id": "shop_config"})
    target_channel = channel or (bot.get_channel(config["channel_id"]) if config else ctx.channel)
    role_mention = role.mention if role else ""

    embed = discord.Embed(
        title="🐹 Tiệm Tạp Hóa Nhà Hamster 🐹",
        description="Chào mừng bạn đến với tiệm cày thuê!\nHãy chọn dịch vụ bên dưới và điền thông tin vào biểu mẫu.",
        color=0xFFB6C1
    )
    
    menu_data = settings_col.find_one({"_id": "shop_menu_ui"})
    view = ShopView()

    if menu_data:
        try:
            ch = bot.get_channel(menu_data["channel_id"])
            msg = await ch.fetch_message(menu_data["message_id"])
            await msg.edit(content=role_mention, embed=embed, view=view)
        except: menu_data = None

    if not menu_data:
        new_msg = await target_channel.send(content=role_mention, embed=embed, view=view)
        settings_col.update_one({"_id": "shop_menu_ui"}, {"$set": {"message_id": new_msg.id, "channel_id": target_channel.id}}, upsert=True)

    await ctx.send(f"✅ Đã cập nhật sản phẩm: **{name}**")

@bot.command()
@commands.has_permissions(administrator=True)
async def setbill(ctx, channel: discord.TextChannel = None):
    target = channel or ctx.channel
    settings_col.update_one({"_id": "bill_config"}, {"$set": {"channel_id": target.id}}, upsert=True)
    await ctx.send(f"📋 Kênh hóa đơn đã được đặt tại: {target.mention}")

@bot.command()
async def work(ctx):
    money = random.randint(1000, 5000)
    users_col.update_one({"_id": ctx.author.id}, {"$inc": {"balance": money}}, upsert=True)
    await ctx.send(f"⚒️ Bạn đã làm việc và nhận được `{money:,.0f} xu`!")

@bot.command()
async def bal(ctx):
    user = get_user(ctx.author.id)
    await ctx.send(f"💰 Số dư: `{user['balance']:,.0f} xu`")

# --- CHẠY ---
@bot.event
async def on_ready(): print(f'✅ Bot {bot.user} đã sẵn sàng!')

keep_alive()
bot.run(os.getenv("BOT_TOKEN"))
