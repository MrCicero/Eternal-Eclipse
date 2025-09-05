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

# Roles allowed to use mod commands
MOD_ROLES = ["Owner", "Co-Owner", "Senior Moderator"]
# Roles that cannot be moderated
PROTECTED_ROLES = ["Owner"]

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

# ---------------- Utils ---------------- #
async def send_dm(member, action, reason, staff, color):
    try:
        embed_dm = discord.Embed(
            title="⚠️ Action Taken Against You",
            color=color,
            timestamp=datetime.utcnow()
        )
        embed_dm.add_field(name="🛠️ Action", value=action, inline=True)
        if staff:
            embed_dm.add_field(name="👮 Staff", value=staff.mention, inline=True)
        embed_dm.add_field(name="📜 Reason", value=reason, inline=False)
        embed_dm.set_footer(text=f"Server: {staff.guild.name if staff else 'System'}")
        await member.send(embed=embed_dm)
    except:
        pass

async def log_action(guild, action, member, staff, reason, color):
    log_channel = discord.utils.get(guild.text_channels, name="💻│mod-logs")
    embed_log = discord.Embed(
        title=f"🔔 Moderation Action: {action}",
        color=color,
        timestamp=datetime.utcnow()
    )
    embed_log.add_field(name="👤 Target", value=member.mention, inline=True)
    if staff:
        embed_log.add_field(name="👮 Staff", value=staff.mention, inline=True)
    embed_log.add_field(name="📜 Reason", value=reason, inline=False)
    if log_channel:
        await log_channel.send(embed=embed_log)
    print(f"{action} | {member} | by {staff} | Reason: {reason}")

async def auto_mute(staff, guild, reason):
    """Mute a moderator for 5 minutes if they try to punish protected roles"""
    role = discord.utils.get(guild.roles, name="muted")
    if role:
        await staff.add_roles(role)
        await send_dm(staff, "Mute (5 Minutes)", reason, None, discord.Color.dark_grey())
        await log_action(guild, "Auto-Mute (5m)", staff, None, reason, discord.Color.dark_grey())

        # Wait 5 minutes then unmute
        await discord.utils.sleep_until(datetime.utcnow() + discord.timedelta(minutes=5))
        if role in staff.roles:
            await staff.remove_roles(role)
            await send_dm(staff, "Unmute", "Your 5 minute mute has expired", None, discord.Color.green())
            await log_action(guild, "Auto-Unmute", staff, None, "Mute expired (5 minutes)", discord.Color.green())

def is_protected(member):
    return any(r.name in PROTECTED_ROLES for r in member.roles)

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
                description=f"✅ Welcome back {message.author.mention}, AFK removed (AFK for {elapsed} sec).",
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
async def handle_protected(interaction, member):
    """Block action + auto-mute abuser"""
    await interaction.response.send_message(
        embed=discord.Embed(
            description=f"❌ {member.mention} is protected. You are muted for 5 minutes.",
            color=discord.Color.red()
        ),
        ephemeral=True
    )
    await auto_mute(interaction.user, interaction.guild, f"Attempted moderation on protected role: {member.display_name}")

@bot.tree.command(name="ban", description="Ban a user")
@is_mod()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if is_protected(member):
        return await handle_protected(interaction, member)
    await send_dm(member, "Ban", reason, interaction.user, discord.Color.red())
    await member.ban(reason=reason)
    await log_action(interaction.guild, "Ban", member, interaction.user, reason, discord.Color.red())
    await interaction.response.send_message(embed=discord.Embed(description=f"🔨 {member} banned. Reason: {reason}", color=discord.Color.red()))

@bot.tree.command(name="kick", description="Kick a user")
@is_mod()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if is_protected(member):
        return await handle_protected(interaction, member)
    await send_dm(member, "Kick", reason, interaction.user, discord.Color.orange())
    await member.kick(reason=reason)
    await log_action(interaction.guild, "Kick", member, interaction.user, reason, discord.Color.orange())
    await interaction.response.send_message(embed=discord.Embed(description=f"👢 {member} kicked. Reason: {reason}", color=discord.Color.orange()))

@bot.tree.command(name="mute", description="Mute a user")
@is_mod()
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if is_protected(member):
        return await handle_protected(interaction, member)
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await member.add_roles(role)
        await send_dm(member, "Mute", reason, interaction.user, discord.Color.dark_grey())
        await log_action(interaction.guild, "Mute", member, interaction.user, reason, discord.Color.dark_grey())
        await interaction.response.send_message(embed=discord.Embed(description=f"🔇 {member} muted.", color=discord.Color.dark_grey()))

@bot.tree.command(name="unmute", description="Unmute a user")
@is_mod()
async def unmute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if is_protected(member):
        return await handle_protected(interaction, member)
    role = discord.utils.get(member.guild.roles, name="muted")
    if role:
        await member.remove_roles(role)
        await send_dm(member, "Unmute", reason, interaction.user, discord.Color.green())
        await log_action(interaction.guild, "Unmute", member, interaction.user, reason, discord.Color.green())
        await interaction.response.send_message(embed=discord.Embed(description=f"🔊 {member} unmuted.", color=discord.Color.green()))

@bot.tree.command(name="warn", description="Warn a user")
@is_mod()
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    if is_protected(member):
        return await handle_protected(interaction, member)
    warnings = load_warnings()
    warnings.setdefault(str(member.id), []).append(reason)
    save_warnings(warnings)
    await send_dm(member, "Warn", reason, interaction.user, discord.Color.gold())
    await log_action(interaction.guild, "Warn", member, interaction.user, reason, discord.Color.gold())
    await interaction.response.send_message(embed=discord.Embed(description=f"⚠️ {member} warned. Reason: {reason}", color=discord.Color.gold()))

@bot.tree.command(name="warnings", description="Check a user's warnings")
@is_mod()
async def warnings(interaction: discord.Interaction, member: discord.Member):
    warns = load_warnings().get(str(member.id), [])
    embed = discord.Embed(
        description=f"{member} has {len(warns)} warnings.\n" + "\n".join([f"- {w}" for w in warns]),
        color=discord.Color.gold()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clearwarn", description="Clear all warnings for a user")
@is_mod()
async def clearwarn(interaction: discord.Interaction, member: discord.Member):
    if is_protected(member):
        return await handle_protected(interaction, member)
    warnings = load_warnings()
    warnings[str(member.id)] = []
    save_warnings(warnings)
    await send_dm(member, "Clear Warnings", "All warnings cleared", interaction.user, discord.Color.blue())
    await log_action(interaction.guild, "Clear Warnings", member, interaction.user, "All warnings cleared", discord.Color.blue())
    await interaction.response.send_message(embed=discord.Embed(description=f"✅ Cleared all warnings for {member}", color=discord.Color.blue()))

# ---------------- Run Bot ---------------- #
keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
