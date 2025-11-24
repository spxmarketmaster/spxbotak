import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime

# =============== NASTAVENÍ ===============

TOKEN = os.getenv("TOKEN")  # token se načte z prostředí (env variable)
GUILD_ID = 1408726786144993283         # ID tvého serveru
LOG_CHANNEL_ID = 1442541562709016606   # ID logovacího kanálu
ADMIN_ROLE_ID = 1408788180097957899    # ID role, která může používat admin příkazy
DATA_FILE = "stock.json"         # soubor, kam se ukládá stock + historie

# =============== DISCORD SETUP ===============

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =============== PRÁCE S "DB" (JSON) ===============

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"stock": {}, "history": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {"stock": {}, "history": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


data = load_data()


def add_stock_items(product: str, items: list[str]):
    product = product.lower()
    if product not in data["stock"]:
        data["stock"][product] = []
    data["stock"][product].extend(items)
    save_data(data)


def pop_stock_item(product: str):
    product = product.lower()
    if product not in data["stock"] or len(data["stock"][product]) == 0:
        return None
    item = data["stock"][product].pop(0)
    save_data(data)
    return item


def get_stock_count(product: str | None = None):
    if product:
        product = product.lower()
        return len(data["stock"].get(product, []))
    else:
        # všechno
        return {p: len(items) for p, items in data["stock"].items()}


def log_delivery(user_id: int, admin_id: int, product: str, item: str, type_: str):
    entry = {
        "user_id": user_id,
        "admin_id": admin_id,
        "product": product.lower(),
        "item": item,
        "type": type_,  # "deliver" nebo "replace"
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    data["history"].append(entry)
    save_data(data)


def get_last_delivery(user_id: int, product: str):
    product = product.lower()
    # Najdeme poslední záznam pro user + product
    for entry in reversed(data["history"]):
        if entry["user_id"] == user_id and entry["product"] == product:
            return entry
    return None

# =============== ROLE CHECK ===============

def has_admin_role(interaction: discord.Interaction) -> bool:
    return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)

def admin_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        if not has_admin_role(interaction):
            await interaction.response.send_message(
                "❌ Nemáš oprávnění používat tento příkaz.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

# =============== EVENTY ===============

@bot.event
async def on_ready():
    print(f"✅ Bot je online jako {bot.user}")
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await tree.sync(guild=guild)
        print(f"Synced {len(synced)} command(s).")
    except Exception as e:
        print("Sync error:", e)

# =============== SLASH COMMANDY ===============

# /addstock – přidá víc řádků za produkt
@tree.command(
    name="addstock",
    description="Přidá položky do stocku (každý řádek = 1 položka).",
    guild=discord.Object(id=GUILD_ID)
)
@admin_only()
async def addstock(
    interaction: discord.Interaction,
    product: str,
    items: str
):
    """
    product: název produktu, např. fortnite-full
    items: text s více řádky (každý řádek jeden účet/kód)
    """
    lines = [line.strip() for line in items.splitlines() if line.strip()]
    if not lines:
        await interaction.response.send_message("⚠️ Nenašel jsem žádné položky ve vstupu.", ephemeral=True)
        return

    add_stock_items(product, lines)
    await interaction.response.send_message(
        f"✅ Přidáno **{len(lines)}** položek do produktu `{product.lower()}`.",
        ephemeral=True
    )


# /stock – ukáže stav stocku
@tree.command(
    name="stock",
    description="Ukáže počet položek ve stocku.",
    guild=discord.Object(id=GUILD_ID)
)
@admin_only()
async def stock(
    interaction: discord.Interaction,
    product: str | None = None
):
    if product:
        count = get_stock_count(product)
        await interaction.response.send_message(
            f"📦 Produkt `{product.lower()}` má **{count}** položek ve stocku.",
            ephemeral=True
        )
    else:
        all_stock = get_stock_count()
        if not all_stock:
            await interaction.response.send_message("📦 Ve stocku nic není.", ephemeral=True)
            return
        msg_lines = ["📦 **Aktuální stock:**"]
        for p, c in all_stock.items():
            msg_lines.append(f"- `{p}`: **{c}** položek")
        await interaction.response.send_message("\n".join(msg_lines), ephemeral=True)


# /deliver – pošle 1 položku do kanálu + log
@tree.command(
    name="deliver",
    description="Pošle 1 položku ze stocku pro uživatele a zaloguje to.",
    guild=discord.Object(id=GUILD_ID)
)
@admin_only()
async def deliver(
    interaction: discord.Interaction,
    product: str,
    member: discord.Member
):
    item = pop_stock_item(product)
    if item is None:
        await interaction.response.send_message(
            f"⚠️ Žádný stock pro produkt `{product.lower()}`.",
            ephemeral=True
        )
        return

    # Odešleme přímo do kanálu, kde byl použit příkaz
    await interaction.response.send_message(
        f"📦 **Deliver pro {member.mention}**\n```{item}```"
    )

    # Log do log kanálu
    log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="📥 Deliver log",
            color=0x2ecc71
        )
        embed.add_field(name="Produkt", value=product.lower(), inline=True)
        embed.add_field(name="Uživatel", value=member.mention, inline=True)
        embed.add_field(name="Admin", value=interaction.user.mention, inline=True)
        embed.add_field(name="Položka", value=f"```{item}```", inline=False)
        embed.timestamp = datetime.utcnow()
        await log_channel.send(embed=embed)

    # uložit do historie
    log_delivery(member.id, interaction.user.id, product, item, "deliver")


# /replace – najde poslední deliver a pošle nový item
@tree.command(
    name="replace",
    description="Pošle náhradní položku pro uživatele (poslední produkt).",
    guild=discord.Object(id=GUILD_ID)
)
@admin_only()
async def replace(
    interaction: discord.Interaction,
    product: str,
    member: discord.Member
):
    last = get_last_delivery(member.id, product)
    if not last:
        await interaction.response.send_message(
            f"⚠️ Nenalezen žádný předchozí deliver pro {member.mention} u produktu `{product.lower()}`.",
            ephemeral=True
        )
        return

    new_item = pop_stock_item(product)
    if new_item is None:
        await interaction.response.send_message(
            f"⚠️ Ve stocku není žádná další položka pro `{product.lower()}`.",
            ephemeral=True
        )
        return

    # Poslat do kanálu
    await interaction.response.send_message(
        f"🔁 **Replace pro {member.mention}**\n"
        f"Stará položka:\n```{last['item']}```\n"
        f"Nová položka:\n```{new_item}```"
    )

    # Log do log kanálu
    log_channel = interaction.client.get_channel(LOG_CHANNEL_ID)
    if log_channel:
        embed = discord.Embed(
            title="🔁 Replace log",
            color=0xf1c40f
        )
        embed.add_field(name="Produkt", value=product.lower(), inline=True)
        embed.add_field(name="Uživatel", value=member.mention, inline=True)
        embed.add_field(name="Admin", value=interaction.user.mention, inline=True)
        embed.add_field(name="Stará položka", value=f"```{last['item']}```", inline=False)
        embed.add_field(name="Nová položka", value=f"```{new_item}```", inline=False)
        embed.timestamp = datetime.utcnow()
        await log_channel.send(embed=embed)

    # uložit do historie jako replace
    log_delivery(member.id, interaction.user.id, product, new_item, "replace")


# =============== START BOTA ===============

if __name__ == "__main__":
    bot.run(TOKEN)
