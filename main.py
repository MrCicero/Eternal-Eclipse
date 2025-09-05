import discord
from discord.ext import commands
import logging
import os
import json
from datetime import datetime

# ----------------------------
# Logging Setup
# ----------------------------
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logging.basicConfig(level=logging.DEBUG)

# ----------------------------
# Bot Setup
# ----------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents, help_command=None)

# ----------------------------
# Constants
# ----------------------------
WELCOME_CHANNEL_ID = 1411797330381770872
LEAVE_CHANNEL_ID = 1411797330381770872
WELCOME_BANNER = "https://cdn.discordapp.com/attachments/1404844685901692969/1413241369178148874/chilljapan.png"
LEAVE_BANNER = "https://cdn.discordapp.com/attachments/1404844685901692969/1413250331743092906/goodbye_banner.png"
MOD_ROLES = ["Owner", "Co-Owner", "Senior Moderator"]
MUTED_ROLE_NAME = "muted"

# AFK storage
afk_users = {}  # {user_id: {"reason": reason, "time": datetime}}

# Warnings storage
if not os.path.exists("warnings.json"):
    with open("warnings.json", "w") as f:
        json.dump({}, f)

# ----------------------------
# Events
# ----------------------------
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user}')
    print(f'Logged in as {bot.user}')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🌑 Eternal Eclipse — Dark Welcome",
            description=f"👁️ A new soul dares to cross the Veil… {member.mention} has entered the Eternal Eclipse.\n\n"
                        f"🔻 To survive the Eclipse:\n"
                        f"⚖️ Read the Eternal Decrees → <#1411797568643530834>\n"
                        f"🩸 Choose your Rite of Power → <#1411798088477179965>\n"
                        f"💎 Give Eclipse their Blessings → <#1411798473606430881>\n"
                        f"🔮 Prove your worth to Ascend → <#1411799087560396860>\n\n"
                        f"🌑 You are Soul **#{len(member.guild.members)}** bound to the Eclipse.\n"
                        f"Your legend begins in darkness… embrace it, or be forgotten.",
            color=0x800080
        )
        embed.set_image(url=WELCOME_BANNER)
        await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(LEAVE_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🕊️ A soul has departed the Eclipse...",
            description=f"{member.mention} has chosen another path beyond the shadows. 🌑\n"
                        f"Their legend ends here, but the realm endures…",
            color=0x800080
        )
        embed.set_image(url=LEAVE_BANNER)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Remove AFK status
    if message.author.id in afk_users:
        try:
            nick = message.author.display_name
            if nick.startswith("[AFK] "):
                new_nick = nick.replace("[AFK] ", "")
                await message.author.edit(nick=new_nick)
        except:
            pass
        del afk_users[message.author.id]
        await message.channel.send(f"Welcome back {message.author.mention}, your AFK is removed.")

    # Notify if mentioned AFK users
    for user_id, data in afk_users.items():
        if bot.get_user(user_id) in message.mentions:
            delta = datetime.utcnow() - data["time"]
            seconds = int(delta.total_seconds())
            await message.channel.send(f"{bot.get_user(user_id).mention} is AFK: {data['reason']} ({seconds} seconds ago)")

    await bot.process_commands(message)

# ----------------------------
# Helpers
# ----------------------------
def is_mod(ctx):
    return any(role.name in MOD_ROLES for role in ctx.author.roles)

# ----------------------------
# Commands
# ----------------------------
@bot.command(name="afk")
async def afk(ctx, *, reason="AFK"):
    try:
        nick = ctx.author.display_name
        if not nick.startswith("[AFK] "):
            await ctx.author.edit(nick=f"[AFK] {nick}")
    except:
        pass
    afk_users[ctx.author.id] = {"reason": reason, "time": datetime.utcnow()}
    embed = discord.Embed(
        title="AFK Set",
        description=f"{ctx.author.mention} is now AFK: {reason}",
        color=0x808080
    )
    await ctx.send(embed=embed)

# Example moderation command: ban
@bot.command(name="ban")
async def ban(ctx, member: discord.Member, *, reason=None):
    if not is_mod(ctx):
        return await ctx.send(embed=discord.Embed(description="You cannot use this command.", color=0x808080))
    await member.ban(reason=reason)
    embed = discord.Embed(description=f"{member} has been banned by {ctx.author}. Reason: {reason}", color=0x808080)
    await ctx.send(embed=embed)

# Example moderation command: kick
@bot.command(name="kick")
async def kick(ctx, member: discord.Member, *, reason=None):
    if not is_mod(ctx):
        return await ctx.send(embed=discord.Embed(description="You cannot use this command.", color=0x808080))
    await member.kick(reason=reason)
    embed = discord.Embed(description=f"{member} has been kicked by {ctx.author}. Reason: {reason}", color=0x808080)
    await ctx.send(embed=embed)

# Example moderation command: mute
@bot.command(name="mute")
async def mute(ctx, member: discord.Member):
    if not is_mod(ctx):
        return await ctx.send(embed=discord.Embed(description="You cannot use this command.", color=0x808080))
    role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if role:
        await member.add_roles(role)
        embed = discord.Embed(description=f"{member} has been muted by {ctx.author}.", color=0x808080)
        await ctx.send(embed=embed)

# Example moderation command: unmute
@bot.command(name="unmute")
async def unmute(ctx, member: discord.Member):
    if not is_mod(ctx):
        return await ctx.send(embed=discord.Embed(description="You cannot use this command.", color=0x808080))
    role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if role:
        await member.remove_roles(role)
        embed = discord.Embed(description=f"{member} has been unmuted by {ctx.author}.", color=0x808080)
        await ctx.send(embed=embed)

# ----------------------------
# Keep adding other commands here with same pattern
# ----------------------------

# ----------------------------
# Run Bot
# ----------------------------
bot.run(os.environ["DISCORD_TOKEN"], log_handler=handler, log_level=logging.DEBUG)
