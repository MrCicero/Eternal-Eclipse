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

# Log channel (replace with your channel ID)
LOG_CHANNEL_ID = 123456789012345678  

# Track uptime
start_time = datetime.utcnow()

# Warnings system
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

# ---------------- Helpers ---------------- #
async def log_action(guild, message):
    channel = guild.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=discord.Embed(
            description=message,
            color=discord.Color.dark_gray()
        ))

def is_mod():
    async def predicate(interaction: discord.Interaction):
        return any(r.name in MOD_ROLES for r in interaction.user.roles)
    return app_commands.check(predicate)

# ---------------- Events ---------------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

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

# ----- Moderator Commands ----- #
@bot.tree.command(name="ban", description="Ban a user")
@is_mod()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    await interaction.response.send_message(embed=discord.Embed(
        description=f"🔨 {member} was banned. Reason: {reason}",
        color=discord.Color.greyple()
    ))
    await log_action(interaction.guild, f"🔨 {member} was banned by {interaction.user}. Reason: {reason}")

@bot.tree.command(name="kick", description="Kick a user")
@is_mod()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await interaction.response.send_message(embed=discord.Embed(
        description=f"👢 {member} was kicked. Reason: {reason}",
        color=discord.Color.greyple()
    ))
    await log_action(interaction.guild, f"👢 {member} was kicked by {interaction.user}. Reason: {reason}")

@bot.tree.command(name="mute", description="Mute a user")
@is_mod()
async def mute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await member.add_roles(role)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"🔇 {member} was muted.",
            color=discord.Color.greyple()
        ))
        await log_action(interaction.guild, f"🔇 {member} was muted by {interaction.user}")

@bot.tree.command(name="unmute", description="Unmute a user")
@is_mod()
async def unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await member.remove_roles(role)
        await interaction.response.send_message(embed=discord.Embed(
            description=f"🔊 {member} was unmuted.",
            color=discord.Color.greyple()
        ))
        await log_action(interaction.guild, f"🔊 {member} was unmuted by {interaction.user}")

@bot.tree.command(name="warn", description="Warn a user")
@is_mod()
@app_commands.checks.cooldown(1, 10)  # 1 use per 10s
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    warnings = load_warnings()
    warnings.setdefault(str(member.id), []).append(reason)
    save_warnings(warnings)

    await interaction.response.send_message(embed=discord.Embed(
        description=f"⚠️ {member} was warned. Reason: {reason}",
        color=discord.Color.greyple()
    ))
    await log_action(interaction.guild, f"⚠️ {member} was warned by {interaction.user}. Reason: {reason}")

    # Auto-mute after 3 warnings
    if len(warnings[str(member.id)]) >= 3:
        role = discord.utils.get(member.guild.roles, name="muted")
        if role:
            await member.add_roles(role)
            await log_action(interaction.guild, f"🔇 {member} auto-muted (3 warnings)")

@bot.tree.command(name="warnings", description="Check a user's warnings")
@is_mod()
async def warnings(interaction: discord.Interaction, member: discord.Member):
    warnings_list = load_warnings().get(str(member.id), [])
    embed = discord.Embed(
        description=f"{member} has {len(warnings_list)} warnings.\n" + "\n".join([f"- {w}" for w in warnings_list]),
        color=discord.Color.greyple()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clearwarn", description="Clear all warnings for a user")
@is_mod()
async def clearwarn(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings()
    warnings[str(member.id)] = []
    save_warnings(warnings)
    await interaction.response.send_message(embed=discord.Embed(
        description=f"✅ Cleared all warnings for {member}",
        color=discord.Color.greyple()
    ))
    await log_action(interaction.guild, f"✅ Cleared warnings for {member}")

# ----- Utility ----- #
@bot.tree.command(name="uptime", description="Check bot uptime")
async def uptime(interaction: discord.Interaction):
    delta = datetime.utcnow() - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await interaction.response.send_message(
        f"⏳ Uptime: {hours}h {minutes}m {seconds}s"
    )

# ---------------- Error Handler ---------------- #
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You don’t have permission for this.", ephemeral=True)
    elif isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏳ Slow down! Try again in {round(error.retry_after, 1)}s.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Something went wrong.", ephemeral=True)
        raise error

# ---------------- Run Bot ---------------- #
keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
