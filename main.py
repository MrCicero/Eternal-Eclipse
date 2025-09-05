import discord
from discord.ext import commands
import json, os, asyncio, datetime

# ==== CONFIG ====
TOKEN = "DISCORD_TOKEN"
PREFIX = "!"
MOD_LOG_CHANNEL = "💻│mod-logs"
MUTED_ROLE = "muted"
OWNER_ROLES = ["Owner", "Co-Owner"]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ==== FILES ====
FILES = ["warnings.json", "timeouts.json", "slurs.json", "caseid.json", "discord.log"]

def ensure_files():
    for f in FILES:
        if not os.path.exists(f):
            if f.endswith(".json"):
                with open(f, "w") as file:
                    if f == "slurs.json":
                        json.dump(["badword1", "badword2"], file)
                    elif f == "caseid.json":
                        json.dump({"last_case_id": 0}, file)
                    else:
                        json.dump({}, file)
            else:
                open(f, "w").close()

ensure_files()

def load_json(name):
    with open(name, "r") as f:
        return json.load(f)

def save_json(name, data):
    with open(name, "w") as f:
        json.dump(data, f, indent=4)

# ==== CASE ID ====
def next_case_id():
    data = load_json("caseid.json")
    data["last_case_id"] += 1
    save_json("caseid.json", data)
    return data["last_case_id"]

# ==== LOGGING ====
async def log_action(guild, action, user, moderator, reason, duration="N/A"):
    case_id = next_case_id()
    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    # Log to discord.log
    with open("discord.log", "a") as f:
        f.write(f"{timestamp} | Case #{case_id} | {action} | User={user} | Mod={moderator} | Reason={reason} | Duration={duration}\n")

    # Embed for 💻│mod-logs
    embed = discord.Embed(title=f"⚡ {action}", color=discord.Color.red())
    embed.add_field(name="👤 User", value=f"{user.mention} ({user.id})", inline=False)
    embed.add_field(name="🛡️ Moderator", value=str(moderator), inline=False)
    embed.add_field(name="⏳ Duration", value=duration, inline=False)
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    embed.add_field(name="📅 Timestamp", value=timestamp, inline=False)
    embed.add_field(name="🆔 Case ID", value=f"#{case_id}", inline=False)

    channel = discord.utils.get(guild.text_channels, name=MOD_LOG_CHANNEL)
    if channel:
        await channel.send(embed=embed)

    # DM the user
    try:
        dm = discord.Embed(title=f"⛔ {action}", color=discord.Color.red())
        dm.add_field(name="⏳ Duration", value=duration, inline=False)
        dm.add_field(name="📝 Reason", value=reason, inline=False)
        dm.add_field(name="📅 Timestamp", value=timestamp, inline=False)
        dm.add_field(name="🆔 Case ID", value=f"#{case_id}", inline=False)
        await user.send(embed=dm)
    except:
        pass

# ==== PROTECTED ROLES ====
def is_protected(member):
    return any(role.name in OWNER_ROLES for role in member.roles)

# ==== AUTO-MOD ====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    slurs = load_json("slurs.json")
    if any(slur in message.content.lower() for slur in slurs):
        await handle_timeout(message, "Slur Detected")
        return

    if "discord.gg/" in message.content or "discord.com/invite/" in message.content:
        await handle_timeout(message, "Invite Link Detected")
        await message.delete()
        return

    await bot.process_commands(message)

async def handle_timeout(message, reason):
    member = message.author
    duration = 2700 if any(r.name in [ "Admin", "Moderator" ] for r in member.roles) else 1800  # 45m mods, 30m normal
    if is_protected(member):
        return

    await member.timeout(discord.utils.utcnow() + datetime.timedelta(seconds=duration))
    await log_action(message.guild, "Timeout", member, "System (Auto)", reason, f"{duration//60} minutes")

# ==== MOD COMMANDS ====
@bot.command()
async def mute(ctx, member: discord.Member, *, reason="No reason"):
    if is_protected(member):
        await ctx.send("❌ You cannot mute protected roles!")
        return
    role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE)
    if role:
        await member.add_roles(role)
        await log_action(ctx.guild, "Mute", member, ctx.author, reason, "Permanent")

@bot.command()
async def unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE)
    if role:
        await member.remove_roles(role)
        await log_action(ctx.guild, "Unmute", member, ctx.author, "Manual Unmute")

@bot.command()
async def timeout(ctx, member: discord.Member, minutes: int, *, reason="No reason"):
    if is_protected(member):
        await ctx.send("❌ You cannot timeout protected roles!")
        return
    await member.timeout(discord.utils.utcnow() + datetime.timedelta(minutes=minutes))
    await log_action(ctx.guild, "Timeout", member, ctx.author, reason, f"{minutes} minutes")

@bot.command()
async def untimeout(ctx, member: discord.Member):
    await member.timeout(None)
    await log_action(ctx.guild, "Untimeout", member, ctx.author, "Manual Untimeout")

@bot.command()
async def warn(ctx, member: discord.Member, *, reason="No reason"):
    warns = load_json("warnings.json")
    user_id = str(member.id)
    warns[user_id] = warns.get(user_id, 0) + 1
    save_json("warnings.json", warns)

    if warns[user_id] >= 3:
        await member.timeout(None)  # Clear existing timeout
        await member.timeout(discord.utils.utcnow() + datetime.timedelta(days=365*10))
        await log_action(ctx.guild, "Permanent Timeout", member, ctx.author, "3 Warnings", "Permanent")
    else:
        await log_action(ctx.guild, "Warn", member, ctx.author, reason)

@bot.command()
async def clearwarn(ctx, member: discord.Member):
    warns = load_json("warnings.json")
    user_id = str(member.id)
    if user_id in warns:
        warns[user_id] = 0
        save_json("warnings.json", warns)
        await log_action(ctx.guild, "Clear Warns", member, ctx.author, "All warns cleared")

# ==== SLUR MANAGEMENT ====
@bot.command()
@commands.has_permissions(administrator=True)
async def addslur(ctx, *, word):
    slurs = load_json("slurs.json")
    slurs.append(word.lower())
    save_json("slurs.json", slurs)
    await ctx.send(f"✅ Slur `{word}` added.")

@bot.command()
@commands.has_permissions(administrator=True)
async def removeslur(ctx, *, word):
    slurs = load_json("slurs.json")
    if word.lower() in slurs:
        slurs.remove(word.lower())
        save_json("slurs.json", slurs)
        await ctx.send(f"✅ Slur `{word}` removed.")
    else:
        await ctx.send("❌ That word isn’t in the slur list.")

# ==== BOT EVENTS ====
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

bot.run(TOKEN)

