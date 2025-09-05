import os
import json
import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from datetime import datetime

# ---------------- Flask Keep-Alive ---------------- #
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ---------------- Discord Bot Setup ---------------- #
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

# Roles allowed to use mod commands
MOD_ROLES = ["Owner", "Co-Owner", "Senior Moderator"]

# Track AFK users
afk_users = {}

# Load warnings
WARNINGS_FILE = "warnings.json"
if not os.path.exists(WARNINGS_FILE):
    with open(WARNINGS_FILE, "w") as f:
        json.dump({}, f)

def load_warnings():
    with open(WARNINGS_FILE, "r") as f:
        return json.load(f)

def save_warnings(data):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------- Events ---------------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# Welcome message
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1411797330381770872)
    if channel:
        embed = discord.Embed(
            title="🌑 Eternal Eclipse — Dark Welcome",
            description=(
                f"👁️ A new soul dares to cross the Veil… {member.mention} has entered the Eternal Eclipse.\n"
                "Here, light is devoured, shadows reign, and only the strong ascend. 🌌\n\n"
                "🔻 To survive the Eclipse:\n"
                "⚖️ Read the Eternal Decrees → <#1411797568643530834>\n"
                "🩸 Choose your Rite of Power → <#1411798088477179965>\n"
                "💎 Give Eclipse their Blessings → <#1411798473606430881>\n"
                "🔮 Prove your worth to Ascend → <#1411799087560396860>\n\n"
                f"🌑 You are Soul **#{len(member.guild.members)}** bound to the Eclipse.\n"
                "Your legend begins in darkness… embrace it, or be forgotten."
            ),
            color=discord.Color.dark_red()
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1404844685901692969/1413241369178148874/chilljapan.png")
        await channel.send(embed=embed)

# Leave message
@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(1411797330381770872)
    if channel:
        embed = discord.Embed(
            title="🕊️ A soul has departed the Eclipse...",
            description=f"{member.mention} has chosen another path beyond the shadows. 🌑\nTheir legend ends here, but the realm endures…",
            color=discord.Color.dark_red()
        )
        embed.set_image(url="https://cdn.discordapp.com/attachments/1404844685901692969/1413250331743092906/goodbye_banner.png")
        await channel.send(embed=embed)

# AFK remove on message
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id in afk_users:
        afk_since = afk_users.pop(message.author.id)
        elapsed = (datetime.utcnow() - afk_since).seconds
        await message.channel.send(
            embed=discord.Embed(
                description=f"✅ Welcome back {message.author.mention}, I removed your AFK (AFK for {elapsed} seconds).",
                color=discord.Color.greyple()
            )
        )
        try:
            await message.author.edit(nick=message.author.display_name.replace("[AFK] ", ""))
        except:
            pass
    await bot.process_commands(message)

# ---------------- Slash Commands ---------------- #
# AFK Command
@bot.tree.command(name="afk", description="Set yourself AFK with a reason")
async def afk(interaction: discord.Interaction, reason: str = "AFK"):
    member = interaction.user
    afk_users[member.id] = datetime.utcnow()
    try:
        await member.edit(nick=f"[AFK] {member.display_name}")
    except:
        pass
    embed = discord.Embed(
        description=f"{member.mention} is now AFK: **{reason}**",
        color=discord.Color.greyple()
    )
    await interaction.response.send_message(embed=embed)

# Check mod role
def is_mod():
    async def predicate(interaction: discord.Interaction):
        return any(r.name in MOD_ROLES for r in interaction.user.roles)
    return app_commands.check(predicate)

# ---------------- Moderator Commands ---------------- #
@bot.tree.command(name="ban", description="Ban a user")
@is_mod()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    embed = discord.Embed(description=f"🔨 {member} was banned. Reason: {reason}", color=discord.Color.greyple())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kick", description="Kick a user")
@is_mod()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    embed = discord.Embed(description=f"👢 {member} was kicked. Reason: {reason}", color=discord.Color.greyple())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mute", description="Mute a user")
@is_mod()
async def mute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await member.add_roles(role)
        embed = discord.Embed(description=f"🔇 {member} was muted.", color=discord.Color.greyple())
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unmute", description="Unmute a user")
@is_mod()
async def unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await member.remove_roles(role)
        embed = discord.Embed(description=f"🔊 {member} was unmuted.", color=discord.Color.greyple())
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warn", description="Warn a user")
@is_mod()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    warnings = load_warnings()
    warnings.setdefault(str(member.id), []).append(reason)
    save_warnings(warnings)
    embed = discord.Embed(description=f"⚠️ {member} was warned. Reason: {reason}", color=discord.Color.greyple())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="warnings", description="Check a user's warnings")
@is_mod()
async def warnings(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings().get(str(member.id), [])
    embed = discord.Embed(
        description=f"{member} has {len(warnings)} warnings.\n" + "\n".join([f"- {w}" for w in warnings]),
        color=discord.Color.greyple()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clearwarn", description="Clear all warnings for a user")
@is_mod()
async def clearwarn(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings()
    warnings[str(member.id)] = []
    save_warnings(warnings)
    embed = discord.Embed(description=f"✅ Cleared all warnings for {member}", color=discord.Color.greyple())
    await interaction.response.send_message(embed=embed)

# ---------------- Run Bot ---------------- #
keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
