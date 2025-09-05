import discord
from discord import app_commands, Embed
from discord.ext import commands
import logging
import os
from datetime import datetime
from threading import Thread
from flask import Flask
import json

# -------------------------
# Logging
# -------------------------
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

# -------------------------
# Intents
# -------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# -------------------------
# Bot Initialization
# -------------------------
bot = commands.Bot(command_prefix="/", intents=intents)

# -------------------------
# AFK System Storage
# -------------------------
afk_users = {}  # {user_id: (reason, time)}

# -------------------------
# Welcome / Leave Channel IDs & Embeds
# -------------------------
WELCOME_CHANNEL_ID = 1411797330381770872
LEAVE_CHANNEL_ID = 1411797330381770872

WELCOME_BANNER = "https://cdn.discordapp.com/attachments/1404844685901692969/1413241369178148874/chilljapan.png"
LEAVE_BANNER = "https://cdn.discordapp.com/attachments/1404844685901692969/1413250331743092906/goodbye_banner.png"

# -------------------------
# Moderator Roles
# -------------------------
MODERATOR_ROLES = ["Owner", "Co-Owner", "Senior Moderator"]

# -------------------------
# Warnings Storage
# -------------------------
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

# -------------------------
# Flask Web Server for Uptime
# -------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_server():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_server).start()

# -------------------------
# Events
# -------------------------
@bot.event
async def on_ready():
    guild = bot.guilds[0]  # sync to first guild
    await bot.tree.sync(guild=guild)
    print(f'Bot logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = Embed(title="🌑 Eternal Eclipse — Dark Welcome",
                      description=(
                          f"👁️ A new soul dares to cross the Veil… {member.mention} has entered the Eternal Eclipse.\n"
                          "Here, light is devoured, shadows reign, and only the strong ascend. 🌌\n\n"
                          "🔻 To survive the Eclipse:\n"
                          f"⚖️ Read the Eternal Decrees → <#1411797568643530834>\n"
                          f"🩸 Choose your Rite of Power → <#1411798088477179965>\n"
                          f"💎 Give Eclipse their Blessings → <#1411798473606430881>\n"
                          f"🔮 Prove your worth to Ascend → <#1411799087560396860>\n\n"
                          f"🌑 You are Soul **#{len(member.guild.members)}** bound to the Eclipse.\n"
                          "Your legend begins in darkness… embrace it, or be forgotten."
                      ),
                      color=0x1A1A1A)
        embed.set_image(url=WELCOME_BANNER)
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel:
        embed = Embed(title="🕊️ A soul has departed the Eclipse...",
                      description=(
                          f"{member.mention} has chosen another path beyond the shadows. 🌑\n"
                          "Their legend ends here, but the realm endures…"
                      ),
                      color=0xFF0000)
        embed.set_image(url=LEAVE_BANNER)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Returning from AFK
    if message.author.id in afk_users:
        try:
            if message.author.nick and "[AFK]" in message.author.nick:
                new_nick = message.author.nick.replace("[AFK] ", "")
                await message.author.edit(nick=new_nick)
        except:
            pass
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back {message.author.mention}, your AFK has been removed.")

    await bot.process_commands(message)

# -------------------------
# Utility Functions
# -------------------------
def is_moderator(interaction):
    return any(role.name in MODERATOR_ROLES for role in interaction.user.roles)

# -------------------------
# Slash Commands
# -------------------------
@bot.tree.command(name="afk", description="Set yourself AFK with a reason")
@app_commands.describe(reason="Reason for going AFK")
async def afk(interaction: discord.Interaction, reason: str = "AFK"):
    user = interaction.user
    afk_users[user.id] = (reason, datetime.utcnow())
    try:
        if user.nick:
            await user.edit(nick=f"[AFK] {user.nick}")
        else:
            await user.edit(nick=f"[AFK] {user.name}")
    except:
        pass
    await interaction.response.send_message(embed=Embed(title="AFK Enabled",
                                                        description=f"{user.mention} is now AFK.\nReason: {reason}\nTime: {datetime.utcnow().strftime('%H:%M:%S')} UTC",
                                                        color=0x808080))

# Example moderation command
@bot.tree.command(name="kick", description="Kick a member (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(member="Member to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(embed=Embed(title="Member Kicked",
                                                        description=f"{member.mention} has been kicked.\nReason: {reason}",
                                                        color=0x808080))

@bot.tree.command(name="ban", description="Ban a member (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(member="Member to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(embed=Embed(title="Member Banned",
                                                        description=f"{member.mention} has been banned.\nReason: {reason}",
                                                        color=0x808080))

@bot.tree.command(name="mute", description="Mute a member (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(member="Member to mute", reason="Reason for mute")
async def mute(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    role = discord.utils.get(member.guild.roles, name="muted")
    await member.add_roles(role)
    await interaction.response.send_message(embed=Embed(title="Member Muted",
                                                        description=f"{member.mention} has been muted.\nReason: {reason}",
                                                        color=0x808080))

@bot.tree.command(name="unmute", description="Unmute a member (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(member="Member to unmute")
async def unmute(interaction: discord.Interaction, member: discord.Member):
    role = discord.utils.get(member.guild.roles, name="muted")
    await member.remove_roles(role)
    await interaction.response.send_message(embed=Embed(title="Member Unmuted",
                                                        description=f"{member.mention} has been unmuted.",
                                                        color=0x808080))

@bot.tree.command(name="warn", description="Warn a member (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(member="Member to warn", reason="Reason for warning")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    warnings = load_warnings()
    member_id = str(member.id)
    if member_id not in warnings:
        warnings[member_id] = []
    warnings[member_id].append({"reason": reason, "by": interaction.user.id, "time": str(datetime.utcnow())})
    save_warnings(warnings)
    await interaction.response.send_message(embed=Embed(title="Member Warned",
                                                        description=f"{member.mention} has been warned.\nReason: {reason}",
                                                        color=0x808080))

@bot.tree.command(name="warnings", description="Check warnings for a member (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(member="Member to check warnings")
async def warnings_cmd(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings()
    member_id = str(member.id)
    member_warns = warnings.get(member_id, [])
    if not member_warns:
        text = "No warnings."
    else:
        text = "\n".join([f"{i+1}. {w['reason']} (by <@{w['by']}>)" for i, w in enumerate(member_warns)])
    await interaction.response.send_message(embed=Embed(title=f"{member.display_name} Warnings",
                                                        description=text,
                                                        color=0x808080))

@bot.tree.command(name="clearwarn", description="Clear warnings for a member (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(member="Member to clear warnings")
async def clearwarn(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings()
    member_id = str(member.id)
    warnings[member_id] = []
    save_warnings(warnings)
    await interaction.response.send_message(embed=Embed(title="Warnings Cleared",
                                                        description=f"All warnings for {member.mention} cleared.",
                                                        color=0x808080))

# Embed Command with Reaction Roles Auto
@bot.tree.command(name="embed", description="Send an embed message with reaction roles")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(title="Title of embed", description="Description of embed", color="Color in hex, e.g., 0x808080")
async def embed(interaction: discord.Interaction, title: str, description: str, color: str = "0x808080"):
    color_int = int(color, 16)
    embed_msg = Embed(title=title, description=description, color=color_int)
    msg = await interaction.channel.send(embed=embed_msg)
    await interaction.response.send_message(f"Embed sent! Message ID: {msg.id}", ephemeral=True)
    # Add reaction roles automatically (example: first reaction gets first role etc.)
    # User can extend this logic

# Send message command
@bot.tree.command(name="sendmsg", description="Send a normal message (Moderators only)")
@app_commands.checks.has_any_roles(*MODERATOR_ROLES)
@app_commands.describe(message="Message content")
async def sendmsg(interaction: discord.Interaction, message: str):
    await interaction.channel.send(message)
    await interaction.response.send_message("Message sent!", ephemeral=True)

# -------------------------
# Run Bot
# -------------------------
bot.run(os.environ["DISCORD_TOKEN"], log_handler=handler, log_level=logging.DEBUG)
