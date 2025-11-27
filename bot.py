import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime
from typing import Optional

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
intents.members = True  # kvůli rolím / admin checku

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ================== JSON STORAGE ==================

def load_data():
    """Load stock & history from JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"stock": {}, "history": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"stock": {}, "history": []}


def save_data(data):
    """Save stock & history to JSON file."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def add_history_entry(user_id: int, product: str, code: str, action: str):
    """Add an entry to history (deliver / replace)."""
    data = load_data()
    data.setdefault("history", [])
    data["history"].append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "product": product,
            "code": code,
            "action": action,  # "deliver" or "replace"
        }
    )
    save_data(data)


def get_stock_for_product(product: str):
    """Ensure product key exists in stock structure and return data dict."""
    data = load_data()
    data.setdefault("stock", {})
    data["stock"].setdefault(product, [])
    return data


async def send_log(
    guild: discord.Guild, message: str, code_block: Optional[str] = None
):
    """Send log message into the log channel."""
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        return

    if code_block:
        await channel.send(f"{message}\n```{code_block}```")
    else:
        await channel.send(message)


def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user has the admin role (by role ID)."""
    # interaction.user je Member, takže má .roles
    return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)


# ================== EVENTS ==================

@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print(f"⚠️ Guild with ID {GUILD_ID} not found.")
        return

    try:
        synced = await tree.sync(guild=guild)
        print(f"✅ Bot is online as {bot.user}")
        print(f"✅ Synced {len(synced)} command(s) to guild {guild.name}.")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


# ================== SLASH COMMANDS ==================

# ---- /ping ---------------------------------------------------------------

@tree.command(name="ping", description="Check if the bot is alive.")
async def ping_cmd(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)


# ---- /addstock -----------------------------------------------------------

@tree.command(name="addstock", description="Add stock lines for a selected product.")
@app_commands.describe(
    items="Each line will be saved as one stock item."
)
@app_commands.choices(product=PRODUCT_CHOICES)
async def addstock_cmd(
    interaction: discord.Interaction,
    product: str,
    items: str
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )
        return

    data = get_stock_for_product(product)

    lines = [line.strip() for line in items.splitlines() if line.strip()]
    if not lines:
        await interaction.response.send_message(
            "⚠️ No valid lines found. Please provide at least one line.",
            ephemeral=True,
        )
        return

    data["stock"][product].extend(lines)
    save_data(data)

    await interaction.response.send_message(
        f"✅ Added **{len(lines)}** item(s) to **{product}**.\n"
        f"Now in stock: **{len(data['stock'][product])}** item(s).",
        ephemeral=True,
    )

    await send_log(
        interaction.guild,
        f"➕ **AddStock** by {interaction.user.mention} for **{product}**",
        "\n".join(lines),
    )


# ---- /stock --------------------------------------------------------------

@tree.command(name="stock", description="Show current stock for all or one product.")
@app_commands.choices(product=PRODUCT_CHOICES)
async def stock_cmd(
    interaction: discord.Interaction,
    product: Optional[str] = None
):
    data = load_data()
    data.setdefault("stock", {})

    if product:
        count = len(data["stock"].get(product, []))
        await interaction.response.send_message(
            f"📦 Stock for **{product}**: **{count}** item(s).",
            ephemeral=True,
        )
        return

    if not data["stock"]:
        await interaction.response.send_message(
            "📦 Stock is currently **empty**.", ephemeral=True
        )
        return

    lines = []
    for prod, items in data["stock"].items():
        lines.append(f"- **{prod}**: {len(items)} item(s)")

    msg = "📦 **Current stock:**\n" + "\n".join(lines)
    await interaction.response.send_message(msg, ephemeral=True)


# ---- /deliver ------------------------------------------------------------

@tree.command(name="deliver", description="Deliver one stock item to a user.")
@app_commands.describe(
    user="User who will receive the product"
)
@app_commands.choices(product=PRODUCT_CHOICES)
async def deliver_cmd(
    interaction: discord.Interaction,
    product: str,
    user: discord.User
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )
        return

    data = get_stock_for_product(product)
    items = data["stock"].get(product, [])

    if not items:
        await interaction.response.send_message(
            OUT_OF_STOCK_MESSAGE,
            ephemeral=False,
        )
        return

    code = items.pop(0)  # take first item from stock
    save_data(data)

    # DM to user
    try:
        await user.send(
            f"📦 **Delivery from {interaction.guild.name}**\n"
            f"🛒 **Product:** `{product}`\n"
            f"💬 **Your code / account:**\n```{code}```"
        )
        dm_status = "✅ DM sent."
    except Exception:
        dm_status = "⚠️ Failed to send DM (user closed DMs?)."

    # Public confirmation
    await interaction.response.send_message(
        f"📦 Delivery for {user.mention}\n"
        f"🛒 **Product:** `{product}`\n"
        f"✅ Item taken from stock.\n"
        f"{dm_status}",
        ephemeral=False,
    )

    add_history_entry(user.id, product, code, "deliver")

    await send_log(
        interaction.guild,
        f"📦 **Deliver** for {user.mention} | Product: **{product}**",
        code,
    )


# ---- /replace ------------------------------------------------------------

@tree.command(
    name="replace",
    description="Replace last delivered item for a user with a new one."
)
@app_commands.describe(
    user="User who will receive a replacement"
)
@app_commands.choices(product=PRODUCT_CHOICES)
async def replace_cmd(
    interaction: discord.Interaction,
    product: str,
    user: discord.User
):
    if not is_admin(interaction):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )
        return

    data = load_data()
    history = data.get("history", [])

    # Find last delivery for this user & product
    last = None
    for entry in reversed(history):
        if entry.get("user_id") == user.id and entry.get("product") == product:
            last = entry
            break

    if last is None:
        await interaction.response.send_message(
            "⚠️ No previous delivery found for this user and product.",
            ephemeral=True,
        )
        return

    # Check stock for replacement
    data = get_stock_for_product(product)
    items = data["stock"].get(product, [])
    if not items:
        await interaction.response.send_message(
            OUT_OF_STOCK_MESSAGE,
            ephemeral=False,
        )
        return

    new_code = items.pop(0)
    save_data(data)

    # DM replacement
    try:
        await user.send(
            f"♻️ **Replacement from {interaction.guild.name}**\n"
            f"🛒 **Product:** `{product}`\n"
            f"💬 **New code / account:**\n```{new_code}```"
        )
        dm_status = "✅ Replacement DM sent."
    except Exception:
        dm_status = "⚠️ Failed to send DM (user closed DMs?)."

    await interaction.response.send_message(
        f"♻️ Replacement for {user.mention}\n"
        f"🛒 **Product:** `{product}`\n"
        f"{dm_status}",
        ephemeral=False,
    )

    add_history_entry(user.id, product, new_code, "replace")

    await send_log(
        interaction.guild,
        f"♻️ **Replace** for {user.mention} | Product: **{product}**",
        new_code,
    )


# ================== RUN BOT ==================

if __name__ == "__main__":
    if not TOKEN:
        print("❌ TOKEN environment variable is missing.")
    else:
        bot.run(TOKEN)
