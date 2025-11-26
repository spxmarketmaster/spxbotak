import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

# ================== SETTINGS ==================

TOKEN = os.getenv("TOKEN")  # Bot token from environment variable

GUILD_ID = 1408726786144993283        # Your server ID
LOG_CHANNEL_ID = 1442541562709016606  # Log channel ID
ADMIN_ROLE_ID = 1408788180097957899   # Admin role ID

DATA_FILE = "stock.json"              # JSON data file

OUT_OF_STOCK_MESSAGE = (
    "Hello Customer, please wait for <@1260340541241954447> to complete the product delivery. 📦\n"
    "Your order is currently being processed, we want to ensure everything goes smoothly and securely.🔒\n"
    "Thank you so much for your patience and understanding — we truly appreciate it! ✨"
)

# ================== PRODUCT CHOICES ==================

PRODUCT_CHOICES = [
    app_commands.Choice(name="Rockstar", value="Rockstar"),
    app_commands.Choice(name="Steam", value="Steam"),
    app_commands.Choice(name="Discord", value="Discord"),
    app_commands.Choice(name="Netflix", value="Netflix"),
    app_commands.Choice(name="Hbo", value="Hbo"),
    app_commands.Choice(name="Ytb", value="Ytb"),
    app_commands.Choice(name="NordVpn", value="NordVpn"),
    app_commands.Choice(name="TunnealBear", value="TunnealBear"),
    app_commands.Choice(name="Disney", value="Disney"),
    app_commands.Choice(name="Paramount", value="Paramount"),
    app_commands.Choice(name="IpVanish", value="IpVanish"),
    app_commands.Choice(name="Spotify", value="Spotify"),
    app_commands.Choice(name="Chatgpt", value="Chatgpt"),
    app_commands.Choice(name="MC", value="MC"),
    app_commands.Choice(name="Canva", value="Canva"),
    app_commands.Choice(name="Robux", value="Robux"),
    app_commands.Choice(name="Gta V", value="Gta V"),
    app_commands.Choice(name="Filmora", value="Filmora"),
    app_commands.Choice(name="Nitro", value="Nitro"),
    app_commands.Choice(name="Capcut", value="Capcut"),
    app_commands.Choice(name="Prime", value="Prime"),
    app_commands.Choice(name="Nba", value="Nba"),
    app_commands.Choice(name="Crunychyroll", value="Crunychyroll"),
    app_commands.Choice(name="Ufc", value="Ufc"),
    app_commands.Choice(name="Doulingo", value="Doulingo"),
    app_commands.Choice(name="Rust", value="Rust"),
    app_commands.Choice(name="OF", value="OF"),
]

# ================== DISCORD SETUP ==================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ================== JSON STORAGE ==================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"stock": {}, "history": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"stock": {}, "history": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def add_history_entry(user_id, product, code, action):
    data = load_data()
    data.setdefault("history", [])
    data["history"].append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "product": product,
            "code": code,
            "action": action,  # deliver / replace
        }
    )
    save_data(data)


def get_stock_for_product(product):
    data = load_data()
    data.setdefault("stock", {})
    data["stock"].setdefault(product, [])
    return data


async def send_log(guild, message, code=None):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        return
    if code:
        await channel.send(f"{message}\n```{code}```")
    else:
        await channel.send(message)


def is_admin(interaction):
    role = interaction.guild.get_role(ADMIN_ROLE_ID)
    return role in interaction.user.roles if role else False


# ================== EVENTS ==================

@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        print(f"Guild {GUILD_ID} not found")
        return

    synced = await tree.sync(guild=guild)
    print(f"Bot is online as {bot.user}")
    print(f"Synced {len(synced)} commands to {guild.name}")


# ================== SLASH COMMANDS ==================

# ---- /addstock --------------------------------------------------------------

@tree.command(name="addstock", description="Add stock for a selected product.")
@app_commands.describe(items="Each line will be saved as one stock item.")
@app_commands.choices(product=PRODUCT_CHOICES)
async def addstock_cmd(interaction, product: str, items: str):

    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ You don't have permission to use this command.", ephemeral=True
        )

    data = get_stock_for_product(product)

    lines = [l.strip() for l in items.splitlines() if l.strip()]
    if not lines:
        return await interaction.response.send_message(
            "⚠️ No valid lines found.", ephemeral=True
        )

    data["stock"][product].extend(lines)
    save_data(data)

    await interaction.response.send_message(
        f"✅ Added **{len(lines)}** item(s) to **{product}**.\n"
        f"Current stock: **{len(data['stock'][product])}**",
        ephemeral=True,
    )

    await send_log(interaction.guild, f"➕ AddStock for {product}", "\n".join(lines))


# ---- /stock -----------------------------------------------------------------

@tree.command(name="stock", description="Show stock.")
@app_commands.choices(product=PRODUCT_CHOICES)
async def stock_cmd(interaction, product: str = None):

    data = load_data()
    data.setdefault("stock", {})

    if product:
        count = len(data["stock"].get(product, []))
        return await interaction.response.send_message(
            f"📦 **{product}** has **{count}** item(s).",
            ephemeral=True,
        )

    if not data["stock"]:
        return await interaction.response.send_message(
            "📦 Stock is empty.", ephemeral=True
        )

    msg = "📦 **Current stock:**\n"
    for p, items in data["stock"].items():
        msg += f"- **{p}**: {len(items)} item(s)\n"

    await interaction.response.send_message(msg, ephemeral=True)


# ---- /deliver ---------------------------------------------------------------

@tree.command(name="deliver", description="Deliver a product to a user.")
@app_commands.describe(user="User to receive the product")
@app_commands.choices(product=PRODUCT_CHOICES)
async def deliver_cmd(interaction, product: str, user: discord.User):

    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ You don't have permission to use this command.", ephemeral=True
        )

    data = get_stock_for_product(product)
    items = data["stock"].get(product, [])

    if not items:
        return await interaction.response.send_message(
            OUT_OF_STOCK_MESSAGE, ephemeral=False
        )

    code = items.pop(0)
    save_data(data)

    # Send DM
    try:
        await user.send(
            f"📦 **Delivery from {interaction.guild.name}**\n"
            f"🛒 Product: `{product}`\n"
            f"💬 Your code/account:\n```{code}```"
        )
        dm = "DM sent"
    except:
        dm = "DM failed (user closed DMs)"

    await interaction.response.send_message(
        f"📦 Delivered **{product}** to {user.mention}\n"
        f"💬 {dm}",
        ephemeral=False,
    )

    add_history_entry(user.id, product, code, "deliver")
    await send_log(interaction.guild, f"📦 Deliver for {user.mention}", code)


# ---- /replace ---------------------------------------------------------------

@tree.command(name="replace", description="Replace last delivered item for a user.")
@app_commands.describe(user="User to receive replacement")
@app_commands.choices(product=PRODUCT_CHOICES)
async def replace_cmd(interaction, product: str, user: discord.User):

    if not is_admin(interaction):
        return await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )

    data = load_data()
    history = data.get("history", [])
    last = None

    for entry in reversed(history):
        if entry["user_id"] == user.id and entry["product"] == product:
            last = entry
            break

    if last is None:
        return await interaction.response.send_message(
            "⚠️ No previous delivery found for this user/product.",
            ephemeral=True,
        )

    stock_data = get_stock_for_product(product)
    items = stock_data["stock"].get(product, [])
    if not items:
        return await interaction.response.send_message(
            OUT_OF_STOCK_MESSAGE, ephemeral=False
        )

    new_code = items.pop(0)
    save_data(stock_data)

    try:
        await user.send(
            f"♻️ **Replacement from {interaction.guild.name}**\n"
            f"🛒 Product: `{product}`\n"
            f"💬 New code/account:\n```{new_code}```"
        )
        dm = "Replacement DM sent"
    except:
        dm = "DM failed"

    await interaction.response.send_message(
        f"♻️ Replaced **{product}** for {user.mention}\n"
        f"💬 {dm}",
        ephemeral=False,
    )

    add_history_entry(user.id, product, new_code, "replace")
    await send_log(interaction.guild, f"♻️ Replace for {user.mention}", new_code)


# ================== RUN BOT ==================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ TOKEN environment variable missing.")
    else:
        bot.run(TOKEN)
