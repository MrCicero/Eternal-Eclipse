import os
import json
import discord
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

MOD_ROLES = ["Owner", "Co-Owner", "Admin", "Moderator", "Trial Moderator", "Helper"]

afk_users = {}

# Warnings file
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

# ---------------- Logging ---------------- #
async def log_action(guild, action, member, staff, reason=""):
    log_channel = discord.utils.get(guild.text_channels, name="admin-logs")
    embed = discord.Embed(
        title=f"{action}",
        color=discord.Color.dark_red(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="👤 Target", value=f"{member} ({member.mention})", inline=False)
    embed.add_field(name="👮 Staff", value=f"{staff} ({staff.mention})", inline=False)
    if reason:
        embed.add_field(name="📜 Reason", value=reason, inline=False)
    if log_channel:
        await log_channel.send(embed=embed)
    print(f"[LOG] {action} | Target: {member} | Staff: {staff} | Reason: {reason}")

# ---------------- Events ---------------- #
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔗 Synced {len(synced)} commands")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

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
                description=f"✅ Welcome back {message.author.mention}, AFK removed (AFK for {elapsed} seconds).",
                color=discord.Color.greyple()
            )
        )
        try:
            await message.author.edit(nick=message.author.display_name.replace("[AFK] ", ""))
        except:
            pass
    await bot.process_commands(message)

# ---------------- Checks ---------------- #
def is_mod():
    async def predicate(interaction: discord.Interaction):
        return any(r.name in MOD_ROLES for r in interaction.user.roles)
    return app_commands.check(predicate)

# ---------------- Helper: DM Embed ---------------- #
async def send_dm(member, action, reason, staff, color, extra=""):
    embed_dm = discord.Embed(
        title="⚠️ Action Taken Against You",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed_dm.add_field(name="🛠️ Action", value=action, inline=True)
    embed_dm.add_field(name="👮 Staff", value=staff.mention, inline=True)
    if reason:
        embed_dm.add_field(name="📜 Reason", value=reason, inline=False)
    if extra:
        embed_dm.add_field(name="ℹ️ Info", value=extra, inline=False)
    embed_dm.set_footer(text=f"Server: {staff.guild.name}")
    try:
        await member.send(embed=embed_dm)
    except:
        pass

# ---------------- Commands ---------------- #
# AFK
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

# Ban
@bot.tree.command(name="ban", description="Ban a user")
@is_mod()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await send_dm(member, "Ban", reason, interaction.user, discord.Color.red())
    await member.ban(reason=reason)
    await interaction.response.send_message(embed=discord.Embed(description=f"🔨 {member} was banned. Reason: {reason}", color=discord.Color.red()))
    await log_action(interaction.guild, "🔨 Ban", member, interaction.user, reason)

# Kick
@bot.tree.command(name="kick", description="Kick a user")
@is_mod()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await send_dm(member, "Kick", reason, interaction.user, discord.Color.orange())
    await member.kick(reason=reason)
    await interaction.response.send_message(embed=discord.Embed(description=f"👢 {member} was kicked. Reason: {reason}", color=discord.Color.orange()))
    await log_action(interaction.guild, "👢 Kick", member, interaction.user, reason)

# Mute
@bot.tree.command(name="mute", description="Mute a user")
@is_mod()
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await send_dm(member, "Mute", reason, interaction.user, discord.Color.dark_grey())
        await member.add_roles(role)
        await interaction.response.send_message(embed=discord.Embed(description=f"🔇 {member} was muted.", color=discord.Color.dark_grey()))
        await log_action(interaction.guild, "🔇 Mute", member, interaction.user, reason)

# Unmute
@bot.tree.command(name="unmute", description="Unmute a user")
@is_mod()
async def unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await send_dm(member, "Unmute", "You may now chat again.", interaction.user, discord.Color.green())
        await member.remove_roles(role)
        await interaction.response.send_message(embed=discord.Embed(description=f"🔊 {member} was unmuted.", color=discord.Color.green()))
        await log_action(interaction.guild, "🔊 Unmute", member, interaction.user)

# Warn
@bot.tree.command(name="warn", description="Warn a user")
@is_mod()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    warnings = load_warnings()
    warnings.setdefault(str(member.id), []).append(reason)
    save_warnings(warnings)

    count = len(warnings[str(member.id)])
    await send_dm(member, "Warning", reason, interaction.user, discord.Color.gold(), extra=f"Total warnings: {count}")
    await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ {member} was warned. Reason: {reason}", color=discord.Color.gold()))
    await log_action(interaction.guild, "⚠️ Warn", member, interaction.user, reason)

    # Auto-mute at 3 warns
    if count >= 3:
        role = discord.utils.get(member.guild.roles, name="muted")
        if role:
            await member.add_roles(role)
            await send_dm(member, "Auto-Mute", "You reached 3 warnings.", interaction.user, discord.Color.dark_grey())
            await log_action(interaction.guild, "🔇 Auto-Mute", member, interaction.user, "3 warnings reached")

# Warnings
@bot.tree.command(name="warnings", description="Check a user's warnings")
@is_mod()
async def warnings(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings().get(str(member.id), [])
    embed = discord.Embed(
        description=f"{member} has {len(warnings)} warnings.\n" + "\n".join([f"- {w}" for w in warnings]),
        color=discord.Color.greyple()
    )
    await interaction.response.send_message(embed=embed)

# Clearwarn
@bot.tree.command(name="clearwarn", description="Clear all warnings for a user")
@is_mod()
async def clearwarn(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings()
    warnings[str(member.id)] = []
    save_warnings(warnings)

    await send_dm(member, "Warnings Cleared", "", interaction.user, discord.Color.blue())
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ Cleared all warnings for {member}", color=discord.Color.blue()))
    await log_action(interaction.guild, "✅ Clearwarn", member, interaction.user)

# Uptime
start_time = datetime.utcnow()

@bot.tree.command(name="uptime", description="Show bot uptime")
async def uptime(interaction: discord.Interaction):
    delta = datetime.utcnow() - start_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"⏱️ Uptime: {hours}h {minutes}m {seconds}s",
            color=discord.Color.greyple()
        )
    )

# Help
@bot.tree.command(name="help", description="Show all commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="📖 Eternal Eclipse Bot Commands", color=discord.Color.greyple())
    embed.add_field(name="AFK", value="`/afk <reason>` — Set yourself AFK", inline=False)
    embed.add_field(name="Moderation", value="`/ban`, `/kick`, `/mute`, `/unmute`, `/warn`, `/warnings`, `/clearwarn`", inline=False)
    embed.add_field(name="Utility", value="`/uptime`, `/help`", inline=False)
    await interaction.response.send_message(embed=embed)

# ---------------- Error Handling ---------------- #
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You don’t have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Error: {error}", ephemeral=True)

# ---------------- Run Bot ---------------- #
keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
