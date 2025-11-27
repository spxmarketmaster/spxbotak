import os
import json
from datetime import datetime
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

# ================== BASIC CONFIG ==================

# ⚠️ Nastav v Renderu env proměnnou TOKEN
TOKEN = os.getenv("TOKEN")

# Tohle si přepiš na ID svého serveru / log kanálu / admin role
GUILD_ID = 1408726786144993283          # ID serveru
LOG_CHANNEL_ID = 1442541562709016606    # ID log kanálu
ADMIN_ROLE_ID = 1408788180097957899     # ID admin role
STAFF_ID = 1260340541241954447          # ID člena, co doručuje (tvůj staff)

DATA_FILE = "stock.json"                # JSON soubor se stockem

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

# ================== DISCORD CLIENT ==================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # kvůli kontrolám role – nezapomeň zapnout v Dev Portalu

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ================== JSON STORAGE ==================

def log(msg: str):
    """Jednoduché logování do konzole."""
    print(f"[BOT] {datetime.utcnow().isoformat()} | {msg}")


def load_data() -> dict:
    """Načte data ze souboru nebo vrátí default strukturu."""
    if not os.path.exists(DATA_FILE):
        log("No data file found, creating new structure.")
        return {"stock": {}, "history": []}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # jistota, že tam jsou klíče
        data.setdefault("stock", {})
        data.setdefault("history", [])
        return data
    except Exception as e:
        log(f"Error loading data file: {e}")
        return {"stock": {}, "history": []}


def save_data(data: dict):
    """Uloží data do JSON souboru."""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        log("Data saved to file.")
    except Exception as e:
        log(f"Error saving data file: {e}")


def add_history_entry(user_id: int, product: str, code: str, action: str):
    """Přidá záznam do historie (deliver / replace)."""
    data = load_data()
    data["history"].append(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "product": product,
            "code": code,
            "action": action,
        }
    )
    save_data(data)
    log(f"History entry added: user={user_id}, product={product}, action={action}")


def get_stock_for_product(product: str) -> dict:
    """Vrátí strukturu dat a zajistí existenci pole pro produkt."""
    data = load_data()
    data["stock"].setdefault(product, [])
    return data


async def send_log(
    guild: Optional[discord.Guild],
    message: str,
    code_block: Optional[str] = None
):
    """Pošle logovací zprávu do log kanálu."""
    if guild is None:
        log("send_log called but guild is None.")
        return

    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel is None:
        log(f"Log channel with ID {LOG_CHANNEL_ID} not found.")
        return

    try:
        if code_block:
            await channel.send(f"{message}\n```{code_block}```")
        else:
            await channel.send(message)
    except Exception as e:
        log(f"Error sending log message: {e}")


def is_admin(interaction: discord.Interaction) -> bool:
    """Check admin role by ID."""
    if not isinstance(interaction.user, discord.Member):
        return False
    return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)


# ================== EVENTS ==================

@bot.event
async def on_ready():
    log(f"Logged in as {bot.user} (ID: {bot.user.id})")

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        log(f"Guild with ID {GUILD_ID} not found. "
            f"Is the bot invited to that server and is GUILD_ID correct?")
        return

    try:
        synced = await tree.sync(guild=guild)
        log(f"Synced {len(synced)} command(s) to guild {guild.name} ({guild.id}).")
        for cmd in synced:
            log(f" - /{cmd.name}")
    except Exception as e:
        log(f"Failed to sync commands: {e}")


# ================== SLASH COMMANDS ==================

@tree.command(name="ping", description="Check if the bot is alive.")
async def ping_cmd(interaction: discord.Interaction):
    log(f"/ping used by {interaction.user} ({interaction.user.id})")
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)


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
    log(f"/addstock used by {interaction.user} ({interaction.user.id}) | product={product}")

    if not is_admin(interaction):
        log(" -> user is not admin, denied.")
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )
        return

    data = get_stock_for_product(product)
    lines = [line.strip() for line in items.splitlines() if line.strip()]

    if not lines:
        log(" -> no valid lines given.")
        await interaction.response.send_message(
            "⚠️ No valid lines found. Please provide at least one line.",
            ephemeral=True,
        )
        return

    data["stock"][product].extend(lines)
    save_data(data)

    log(f" -> added {len(lines)} line(s) to {product}. Now {len(data['stock'][product])} in stock.")

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


@tree.command(name="stock", description="Show current stock for all or one product.")
@app_commands.choices(product=PRODUCT_CHOICES)
async def stock_cmd(
    interaction: discord.Interaction,
    product: Optional[str] = None
):
    log(f"/stock used by {interaction.user} ({interaction.user.id}) | product={product}")
    data = load_data()

    if product:
        count = len(data["stock"].get(product, []))
        await interaction.response.send_message(
            f"📦 Stock for **{product}**: **{count}** item(s).",
            ephemeral=True,
        )
        return

    if not data["stock"]:
        await interaction.response.send_message(
            "📦 Stock is currently **empty**.",
            ephemeral=True,
        )
        return

    lines = [
        f"- **{prod}**: {len(items)} item(s)"
        for prod, items in data["stock"].items()
    ]

    msg = "📦 **Current stock:**\n" + "\n".join(lines)
    await interaction.response.send_message(msg, ephemeral=True)


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
    log(f"/deliver used by {interaction.user} ({interaction.user.id}) "
        f"| product={product}, target={user.id}")

    if not is_admin(interaction):
        log(" -> user is not admin, denied.")
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )
        return

    data = get_stock_for_product(product)
    items = data["stock"].get(product, [])

    if not items:
        log(" -> stock empty, sending wait message.")
        # zpráva, co jsi chtěl pro shop
        msg = (
            f"Hello {interaction.user.mention}, please wait for <@{STAFF_ID}> "
            f"to complete the product delivery. 📦\n"
            "Your order is currently being processed, we want to ensure everything "
            "goes smoothly and securely.🔒\n"
            "Thank you so much for your patience and understanding — we truly appreciate it! ✨"
        )
        await interaction.response.send_message(msg, ephemeral=False)
        return

    code = items.pop(0)  # vezme první kód
    save_data(data)

    # DM pro zákazníka
    try:
        await user.send(
            f"📦 **Delivery from {interaction.guild.name}**\n"
            f"🛒 **Product:** `{product}`\n"
            f"💬 **Your code / account:**\n```{code}```"
        )
        dm_status = "✅ DM sent."
        log(" -> DM sent successfully.")
    except Exception as e:
        dm_status = "⚠️ Failed to send DM (user closed DMs?)."
        log(f" -> error sending DM: {e}")

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
    log(f"/replace used by {interaction.user} ({interaction.user.id}) "
        f"| product={product}, target={user.id}")

    if not is_admin(interaction):
        log(" -> user is not admin, denied.")
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True,
        )
        return

    data = load_data()
    history = data.get("history", [])

    last = None
    for entry in reversed(history):
        if entry.get("user_id") == user.id and entry.get("product") == product:
            last = entry
            break

    if last is None:
        log(" -> no previous delivery found.")
        await interaction.response.send_message(
            "⚠️ No previous delivery found for this user and product.",
            ephemeral=True,
        )
        return

    data = get_stock_for_product(product)
    items = data["stock"].get(product, [])

    if not items:
        log(" -> stock empty for replacement, sending wait message.")
        msg = (
            f"Hello {interaction.user.mention}, please wait for <@{STAFF_ID}> "
            f"to complete the product delivery. 📦\n"
            "Your order is currently being processed, we want to ensure everything "
            "goes smoothly and securely.🔒\n"
            "Thank you so much for your patience and understanding — we truly appreciate it! ✨"
        )
        await interaction.response.send_message(msg, ephemeral=False)
        return

    new_code = items.pop(0)
    save_data(data)

    try:
        await user.send(
            f"♻️ **Replacement from {interaction.guild.name}**\n"
            f"🛒 **Product:** `{product}`\n"
            f"💬 **New code / account:**\n```{new_code}```"
        )
        dm_status = "✅ Replacement DM sent."
        log(" -> replacement DM sent successfully.")
    except Exception as e:
        dm_status = "⚠️ Failed to send DM (user closed DMs?)."
        log(f" -> error sending replacement DM: {e}")

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
        log("❌ TOKEN environment variable is missing. Set TOKEN in Render env vars.")
    else:
        log("Starting bot...")
        # Na Renderu používej Background Worker, start command např.:
        # python3 bot.py
        bot.run(TOKEN)
