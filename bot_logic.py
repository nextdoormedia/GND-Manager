import discord
from discord.ext import commands
from datetime import datetime
import os, random, json, time, asyncio

# --- INTENTS SETUP (CRITICAL!) ---
# Declare all necessary intents, especially the privileged ones
intents = discord.Intents.default()
# Required for Vibe system, user roles, and managing members
intents.members = True          
# CRITICAL for prefix commands (like !say) and on_message filters
intents.message_content = True  

# --- BOT INITIALIZATION ---
# Pass the explicit intents to the Bot constructor
bot = commands.Bot(command_prefix='!', intents=intents)

Month!")

# --- GLOBAL COMMAND ERROR HANDLER ---
@bot.event
async def on_command_error(ctx, error):
    # This prevents handling errors at the command level if they are ignored
    if hasattr(ctx.command, 'on_error'):
        return

    # User Permission Check Failure
    if isinstance(error, commands.MissingPermissions):
        missing = [p.replace('_', ' ').title() for p in error.missing_permissions]
        await ctx.send(f"❌ **User Error:** You need the following permission(s) to use this command: **{', '.join(missing)}**")
        return

    # Bot Permission Check Failure (This is the one we really need!)
    if isinstance(error, commands.BotMissingPermissions):
        missing = [p.replace('_', ' ').title() for p in error.missing_permissions]
        await ctx.send(f"⚠️ **Bot Error:** I am missing the following permission(s) to run this command: **{', '.join(missing)}**. Please check my role hierarchy and channel overrides.")
        return
    
    # Missing Argument Failure (e.g., typing !say without a channel)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ **Syntax Error:** Missing required argument: `{error.param.name}`. Correct usage is `!say #channel_name Your Message`")
        return

    # Target Not Found (e.g., trying to use !say on a channel that doesn't exist)
    if isinstance(error, commands.ChannelNotFound):
        await ctx.send(f"❌ **Channel Not Found:** I couldn't find the channel you specified. Please make sure the channel name is correct.")
        return
    
    # For any other unexpected error, print to the console for debugging
    print(f"Ignoring exception in command {ctx.command}:")
    raise error

# --- CONFIGURATION CONSTANTS ---
DATABASE_FILE = "vibe_data.json"
COOLDOWN_SECONDS = 15
MAX_VIBE_FOR_PRESTIGE = 2000
DAILY_VIBE_BASE = 50
DAILY_VIBE_STREAK_BONUS = 5
VIBE_PER_MESSAGE = (1, 3) 
WELCOME_CHANNEL_ID = 1420121916404007136 # REPLACE ME
MOD_ALERTS_CHANNEL_ID = 1420127688248660081 # REPLACE ME
SELF_PROMO_CHANNEL_NAME = "self-promo"
FILTERED_KEYWORDS = ["illegal content", "graphic violence", "shock video", "dtxduo impersonation", "official admin", "mod giveaway"]
SPAM_LINKS = ["bit.ly", "tinyurl", "ow.ly", "shorte.st"]
PROMOTION_KEYWORDS = ["subscribe", "patreon", "youtube", "twitch", "onlyfans", "my channel", "check out my"]
VIBE_RANKS = {"New Neighbor": 0, "Familiar Face": 100, "Resident": 250, "Housemate": 500, "Block Captain": MAX_VIBE_FOR_PRESTIGE}
VIBE_SHOP_ITEMS = {1: {"name": "Icon", "cost": 500, "description": "Icon"}, 2: {"name": "Flair", "cost": 1000, "description": "Flair"}, 3: {"name": "Custom Photo", "cost": 2500, "description": "Custom Photo"}, 4: {"name": "DM Chat Pass", "cost": 7500, "description": "DM Chat Pass"}, 5: {"name": "VC/Cam Pass", "cost": 20000, "description": "VC/Cam Pass"}}

# --- DATABASE / CORE HELPERS ---
def load_data():
    if not os.path.exists(DATABASE_FILE) or os.path.getsize(DATABASE_FILE) == 0: return {}
    try:
        with open(DATABASE_FILE, 'r') as f: return json.load(f)
    except json.JSONDecodeError: return {}

def save_data(data):
    with open(DATABASE_FILE, 'w') as f: json.dump(data, f, indent=4)

vibe_data = load_data()
last_vibe_time = {}

def get_user_data(user_id):
    user_id_str = str(user_id)
    if user_id_str not in vibe_data:
        vibe_data[user_id_str] = {"vibe": 0, "level": 1, "name": "Unknown", "total_vibe_earned": 0, "last_daily_claim": 0, "streak": 0, "prestige_level": 0, "flair": "A friendly neighbor.", "nickname_icon": "🏠", "vibe_logs": []}
    if 'prestige_level' not in vibe_data[user_id_str]:
        vibe_data[user_id_str]['prestige_level'] = 0; vibe_data[user_id_str]['flair'] = "A friendly neighbor."; vibe_data[user_id_str]['nickname_icon'] = "🏠"; vibe_data[user_id_str]['total_vibe_earned'] = vibe_data[user_id_str]['vibe']; vibe_data[user_id_str]['vibe_logs'] = []
    return vibe_data[user_id_str]

def get_vibe_rank_name(vibe):
    rank_name = "New Neighbor"
    for name, threshold in VIBE_RANKS.items():
        if vibe >= threshold: rank_name = name
    return rank_name

async def check_and_update_rank(member, user_data, old_vibe):
    current_rank_name = get_vibe_rank_name(user_data['vibe'])
    old_rank_name = get_vibe_rank_name(old_vibe)

    if current_rank_name != old_rank_name:
        guild = member.guild
        try:
            for name in VIBE_RANKS:
                role = discord.utils.get(guild.roles, name=name)
                if role and role in member.roles: await member.remove_roles(role)
            new_role = discord.utils.get(guild.roles, name=current_rank_name)
            if new_role: await member.add_roles(new_role)
            welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
            if welcome_channel: await welcome_channel.send(f"🎉 **{member.display_name}** has moved up the block to **{current_rank_name}**!")
        except Exception as e: print(f"Error updating roles: {e}")

async def log_mod_action(guild, action_type, target_user, reason, vibe_change=None):
    mod_channel = guild.get_channel(MOD_ALERTS_CHANNEL_ID)
    if mod_channel:
        embed = discord.Embed(title=f"🚨 MOD LOG: {action_type}", color=discord.Color.red())
        embed.add_field(name="Target", value=f"{target_user.mention} (`{target_user.id}`)", inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        if vibe_change is not None: embed.add_field(name="Vibe Adjustment", value=f"{vibe_change}", inline=True)
        await mod_channel.send(embed=embed)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="Managing the Neighborhood"))

# --- RULE ENFORCEMENT AND VIBE GAIN ---
@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None: return

    user_id = str(message.author.id)
    content = message.content.lower()
    if content.startswith(bot.command_prefix): await bot.process_commands(message); return

    is_violation = False
    violation_reason = ""
    
    for keyword in FILTERED_KEYWORDS:
        if keyword in content: is_violation = True; violation_reason = f"Content Guideline/Impersonation violation (Keyword: {keyword})"; break
    
    if not is_violation:
        for link in SPAM_LINKS:
            if link in content: is_violation = True; violation_reason = "Suspicious/Shortened Link (Potential Spam/Phishing)"; break

    if is_violation:
        await message.delete()
        try:
            warning = await message.channel.send(f"🛑 {message.author.mention}, your message has been removed. Reason: **{violation_reason}**.")
            await warning.delete(delay=5)
            await log_mod_action(message.guild, "Message Deleted", message.author, violation_reason)
        except Exception: pass
        return

    if message.channel.name != SELF_PROMO_CHANNEL_NAME:
        for keyword in PROMOTION_KEYWORDS:
            if keyword in content:
                warning = await message.channel.send(f"🔔 {message.author.mention}, that looks like self-promotion. Please use the **#{SELF_PROMO_CHANNEL_NAME}** channel to share your links.")
                await warning.delete(delay=8)
                last_vibe_time[user_id] = time.time() + COOLDOWN_SECONDS * 2
                return

    if user_id not in last_vibe_time or (time.time() - last_vibe_time[user_id] >= COOLDOWN_SECONDS):
        user_data = get_user_data(user_id)
        vibe_gained = random.randint(*VIBE_PER_MESSAGE)
        old_vibe = user_data['vibe']

        user_data['vibe'] += vibe_gained
        user_data['total_vibe_earned'] += vibe_gained
        user_data['name'] = message.author.name
        last_vibe_time[user_id] = time.time()
        
        await check_and_update_rank(message.author, user_data, old_vibe)
        save_data(vibe_data)

# --- VIBE ECONOMY COMMANDS ---
@bot.command()
async def daily(ctx):
    user_id = str(ctx.author.id); user_data = get_user_data(user_id); last_claim = user_data.get('last_daily_claim', 0); current_time = int(time.time())
    if current_time - last_claim < 86400: await ctx.send(f"🕰️ **Chill out!** You've already claimed your daily Vibe today."); return

    current_streak = user_data.get('streak', 0) + 1
    vibe_gained = DAILY_VIBE_BASE + (current_streak * DAILY_VIBE_STREAK_BONUS)
    old_vibe = user_data['vibe']
    user_data['vibe'] += vibe_gained; user_data['total_vibe_earned'] += vibe_gained; user_data['last_daily_claim'] = current_time; user_data['streak'] = current_streak
    await check_and_update_rank(ctx.author, user_data, old_vibe); save_data(vibe_data)

    embed = discord.Embed(title="DAILY VIBE CLAIMED! 🎉", description=f"You earned **{vibe_gained} Vibe**!", color=discord.Color.green())
    embed.add_field(name="Current Streak", value=f"🔥 {current_streak} Day(s)", inline=False); await ctx.send(embed=embed)

@bot.command()
async def rank(ctx):
    user_data = get_user_data(ctx.author.id); rank_name = get_vibe_rank_name(user_data['vibe']); next_rank_name = None; next_rank_vibe = 0
    sorted_ranks = sorted([(v, n) for n, v in VIBE_RANKS.items() if v > user_data['vibe']])
    if sorted_ranks: next_rank_vibe, next_rank_name = sorted_ranks[0]; vibe_needed = next_rank_vibe - user_data['vibe']; progress_percent = (user_data['vibe'] / next_rank_vibe) * 100
    else: vibe_needed = 0; progress_percent = 100

    embed = discord.Embed(title=f"{user_data['nickname_icon']} {ctx.author.display_name}'s Vibe Status", color=discord.Color.blue())
    embed.add_field(name="Vibe Rank", value=f"**{rank_name}**", inline=True); embed.add_field(name="Current Vibe", value=f"{user_data['vibe']} Vibe", inline=True)
    if next_rank_name: embed.add_field(name="Next Rank Goal", value=f"{vibe_needed} Vibe needed for **{next_rank_name}**", inline=False)
    else: embed.add_field(name="Max Rank Achieved!", value=f"You are a Block Captain! Use `!prestige` to earn Legacy Status.", inline=False)
    embed.set_footer(text=user_data['flair']); await ctx.send(embed=embed)

@bot.command()
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author; user_data = get_user_data(member.id); rank_name = get_vibe_rank_name(user_data['vibe'])
    prestige_status = f"⭐ Legacy Resident {user_data['prestige_level']}" if user_data['prestige_level'] > 0 else "None"

    embed = discord.Embed(title=f"{user_data['nickname_icon']} {member.display_name}'s Vibe Profile", description=f"***{user_data['flair']}***", color=discord.Color.purple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Vibe Rank", value=rank_name, inline=True); embed.add_field(name="Prestige Tier", value=prestige_status, inline=True)
    embed.add_field(name="Total Vibe Earned", value=f"{user_data['total_vibe_earned']} Vibe", inline=True); embed.add_field(name="Current Streak", value=f"{user_data['streak']} Days 🔥", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    leaderboard_data = {data['name']: data['vibe'] for data in vibe_data.values() if data['name'] != "Unknown"}
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True); leaderboard_string = ""
    for i, (name, vibe) in enumerate(sorted_leaderboard[:10]): leaderboard_string += f"**{i+1}.** {name} - {vibe} Vibe\n"
    if not leaderboard_string: leaderboard_string = "No Vibe earned yet! Start chatting!"

    embed = discord.Embed(title="🏆 Top 10 Most Active Neighbors (Vibe Leaderboard)", description=leaderboard_string, color=discord.Color.gold())
    await ctx.send(embed=embed)

@bot.command()
async def prestige(ctx):
    user_data = get_user_data(ctx.author.id)
    if user_data['vibe'] < MAX_VIBE_FOR_PRESTIGE: await ctx.send(f"❌ You must be a **Block Captain** with {MAX_VIBE_FOR_PRESTIGE} Vibe to achieve Prestige Status. Keep grinding!"); return

    user_data['prestige_level'] += 1; user_data['vibe'] = 0; user_data['level'] = 1
    prestige_role_name = f"Legacy Resident {user_data['prestige_level']}"
    
    try:
        prestige_role = discord.utils.get(ctx.guild.roles, name=prestige_role_name)
        if prestige_role: await ctx.author.add_roles(prestige_role)
    except Exception as e: print(f"Error assigning prestige role: {e}")
        
    save_data(vibe_data)
    await ctx.send(f"✨ **LEGACY ACHIEVED!** {ctx.author.mention} is now a **{prestige_role_name}**! Your Vibe has been reset, but your legacy is permanent.")

# --- VIBE SHOP / ECONOMY ---
@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 The Vibe Shop: What Your Vibe Buys", description="Spend your hard-earned Vibe on exclusive content and customization!", color=discord.Color.orange())
    for id, item in VIBE_SHOP_ITEMS.items(): embed.add_field(name=f"#{id}: {item['name']} ({item['cost']} Vibe)", value=item['description'], inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item_id: int):
    user_data = get_user_data(ctx.author.id)
    if item_id not in VIBE_SHOP_ITEMS: await ctx.send("❌ Invalid item ID. Use `!shop` to see available items."); return
    item = VIBE_SHOP_ITEMS[item_id]
    if user_data['vibe'] < item['cost']: await ctx.send(f"❌ You only have {user_data['vibe']} Vibe. You need {item['cost']} Vibe to buy **{item['name']}**."); return

    user_data['vibe'] -= item['cost']; save_data(vibe_data)

    await ctx.send(f"✅ **PURCHASE SUCCESSFUL!** You bought **{item['name']}** for {item['cost']} Vibe.")
    
    mod_channel = ctx.guild.get_channel(MOD_ALERTS_CHANNEL_ID)
    if mod_channel:
        fulfillment_embed = discord.Embed(title="💰 VIBE SHOP PURCHASE ALERT (Action Required)", description=f"Item purchased: **{item['name']}**", color=discord.Color.yellow())
        fulfillment_embed.add_field(name="Buyer", value=f"{ctx.author.mention}", inline=True); fulfillment_embed.add_field(name="Cost", value=f"{item['cost']} Vibe", inline=True); fulfillment_embed.add_field(name="Fulfillment Note", value=item['description'], inline=False)
        await mod_channel.send(embed=fulfillment_embed)

# --- MODERATION & ADMIN UTILITIES ---
@bot.command()
@commands.has_permissions(administrator=True)
async def vibe_penalty(ctx, member: discord.Member, amount: int, *, reason: str):
    user_data = get_user_data(member.id); amount = abs(amount); old_vibe = user_data['vibe']
    user_data['vibe'] = max(0, user_data['vibe'] - amount)
    user_data['vibe_logs'].append({"timestamp": time.time(), "type": "PENALTY", "amount": -amount, "reason": reason, "moderator": ctx.author.name})
    await check_and_update_rank(member, user_data, old_vibe); save_data(vibe_data)
    await ctx.send(f"✅ **Vibe Penalty Applied:** Deducted {amount} Vibe from {member.display_name}. New Vibe: {user_data['vibe']}")
    await log_mod_action(ctx.guild, "Vibe Penalty", member, reason, vibe_change=f"-{amount}")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_flair(ctx, member: discord.Member, *, flair_text: str):
    user_data = get_user_data(member.id); user_data['flair'] = flair_text[:50]; save_data(vibe_data)
    await ctx.send(f"✅ **Flair Updated:** Set flair for {member.display_name} to: *{flair_text}*")

@bot.command()
@commands.has_permissions(administrator=True)
async def set_icon(ctx, member: discord.Member, icon: str):
    user_data = get_user_data(member.id); user_data['nickname_icon'] = icon[:2]; save_data(vibe_data)
    await ctx.send(f"✅ **Icon Updated:** Set icon for {member.display_name} to: {icon}")

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, channel: discord.TextChannel, *, message: str):
    try: await channel.send(message); await ctx.message.delete()
    except Exception as e: await ctx.send(f"❌ Could not post message to {channel.mention}. Error: {e}")

# --- COMMUNITY UTILITIES ---
@bot.command()
async def report(ctx, member: discord.Member, *, reason: str):
    mod_channel = ctx.guild.get_channel(MOD_ALERTS_CHANNEL_ID)
    if mod_channel:
        embed = discord.Embed(title="⚠️ USER REPORT", color=discord.Color.red())
        embed.add_field(name="Reported User", value=member.mention, inline=True); embed.add_field(name="Reported By", value=ctx.author.mention, inline=True); embed.add_field(name="Reason", value=reason, inline=False)
        await mod_channel.send(embed=embed); await ctx.message.delete(); await ctx.author.send(f"✅ Your report against {member.display_name} has been sent.")
    else: await ctx.send("❌ Cannot find the moderation alerts channel.")

@bot.command()
async def nom_vote(ctx, member: discord.Member):
    await ctx.send(f"✅ You voted for **{member.display_name}** for Neighbor of the 
