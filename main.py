import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
from flask import Flask
import logging

# ---------- Logging ----------
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logging.basicConfig(level=logging.DEBUG)

# ---------- Bot Setup ----------
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# ---------- Flask for uptime ----------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=8080)

# ---------- Warnings System ----------
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

# ---------- AFK System ----------
afk_data = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # AFK return check
    if message.author.id in afk_data:
        afk_data.pop(message.author.id)
        try:
            nickname = str(message.author.display_name)
            if nickname.startswith("[AFK] "):
                await message.author.edit(nick=nickname.replace("[AFK] ", ""))
        except:
            pass
        await message.channel.send(f"Welcome back {message.author.mention}, your AFK has been removed.")

    # Check mentions
    for user in message.mentions:
        if user.id in afk_data:
            duration = datetime.now() - afk_data[user.id]['time']
            await message.channel.send(
                f"{user.mention} is currently AFK: {afk_data[user.id]['reason']} ({int(duration.total_seconds())} seconds ago)"
            )

    await bot.process_commands(message)

# ---------- Commands ----------
MOD_ROLES = ["Owner", "Co-Owner", "Senior Moderator"]

def is_mod(ctx):
    return any(role.name in MOD_ROLES for role in ctx.author.roles)

@bot.slash_command(name="afk", description="Set yourself AFK with a reason")
async def afk(ctx, *, reason="AFK"):
    afk_data[ctx.author.id] = {'reason': reason, 'time': datetime.now()}
    try:
        await ctx.author.edit(nick=f"[AFK] {ctx.author.display_name}")
    except:
        pass
    await ctx.respond(f"{ctx.author.mention} is now AFK: {reason}")

@bot.slash_command(name="ban", description="Ban a member (Moderator only)")
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    if not is_mod(ctx):
        await ctx.respond("You cannot use this command!")
        return
    await member.ban(reason=reason)
    await ctx.respond(embed=discord.Embed(title=f"{member} was banned", description=reason, color=0x808080))

@bot.slash_command(name="kick", description="Kick a member (Moderator only)")
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    if not is_mod(ctx):
        await ctx.respond("You cannot use this command!")
        return
    await member.kick(reason=reason)
    await ctx.respond(embed=discord.Embed(title=f"{member} was kicked", description=reason, color=0x808080))

@bot.slash_command(name="mute", description="Mute a member (Moderator only)")
async def mute(ctx, member: discord.Member):
    if not is_mod(ctx):
        await ctx.respond("You cannot use this command!")
        return
    role = discord.utils.get(ctx.guild.roles, name="muted")
    if role:
        await member.add_roles(role)
        await ctx.respond(embed=discord.Embed(title=f"{member} was muted", color=0x808080))
    else:
        await ctx.respond("Muted role not found!")

@bot.slash_command(name="unmute", description="Unmute a member (Moderator only)")
async def unmute(ctx, member: discord.Member):
    if not is_mod(ctx):
        await ctx.respond("You cannot use this command!")
        return
    role = discord.utils.get(ctx.guild.roles, name="muted")
    if role:
        await member.remove_roles(role)
        await ctx.respond(embed=discord.Embed(title=f"{member} was unmuted", color=0x808080))
    else:
        await ctx.respond("Muted role not found!")

# You can continue similarly for embed, clearwarn, configure, reactrole, sendmsg, warn, warnings commands

# ---------- Welcome & Leave Messages ----------
WELCOME_CHANNEL = 1411797330381770872
LEAVE_CHANNEL = 1411797330381770872
WELCOME_BANNER = "https://cdn.discordapp.com/attachments/1404844685901692969/1413241369178148874/chilljapan.png"
LEAVE_BANNER = "https://cdn.discordapp.com/attachments/1404844685901692969/1413250331743092906/goodbye_banner.png"

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL)
    embed = discord.Embed(
        title="🌑 Eternal Eclipse — Dark Welcome",
        description=(
            f"👁️ A new soul dares to cross the Veil… {member.mention} has entered the Eternal Eclipse.\n\n"
            f"🔻 To survive the Eclipse:\n"
            f"⚖️ Read the Eternal Decrees → <#1411797568643530834>\n"
            f"🩸 Choose your Rite of Power → <#1411798088477179965>\n"
            f"💎 Give Eclipse their Blessings → <#1411798473606430881>\n"
            f"🔮 Prove your worth to Ascend → <#1411799087560396860>\n\n"
            f"🌑 You are Soul **#{len(member.guild.members)}** bound to the Eclipse.\n"
            "Your legend begins in darkness… embrace it, or be forgotten."
        ),
        color=0x2f3136
    )
    embed.set_image(url=WELCOME_BANNER)
    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL)
    embed = discord.Embed(
        title="🕊️ A soul has departed the Eclipse...",
        description=f"{member.mention} has chosen another path beyond the shadows. 🌑\nTheir legend ends here, but the realm endures…",
        color=0x2f3136
    )
    embed.set_image(url=LEAVE_BANNER)
    await channel.send(embed=embed)

# ---------- Bot Ready ----------
@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')

# ---------- Run Flask ----------
import threading
threading.Thread(target=run_flask).start()

# ---------- Run Bot ----------
bot.run(os.environ["DISCORD_TOKEN"], log_handler=handler, log_level=logging.DEBUG)
