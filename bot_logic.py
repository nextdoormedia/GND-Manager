import discord
from discord.ext import commands
from datetime import datetime
import os, random, json, time, asyncio

# --- CONFIGURATION CONSTANTS (Control Panel) ---
# CRITICAL NOTE: Replace the Example IDs below with your server's actual IDs
DATABASE_FILE = "vibe_data.json"
COOLDOWN_SECONDS = 15
MAX_VIBE_FOR_PRESTIGE = 2000
DAILY_VIBE_BASE = 50
DAILY_VIBE_STREAK_BONUS = 5
VIBE_PER_MESSAGE = (1, 3) 

# CRITICAL IDs: REPLACE THESE WITH YOUR SERVER'S ACTUAL IDs
WELCOME_CHANNEL_ID = 1420121916404007136    # The channel where the rules/verification message is.
VERIFICATION_MESSAGE_ID = 1420121916404007137 # The specific rules message users react to.
VERIFICATION_EMOJI = "✅"                 # The specific emoji users react with.
MEMBER_ROLE_NAME = "Member"              # The role to grant upon verification.

MOD_ALERTS_CHANNEL_ID = 1420127688248660081 
SELF_PROMO_CHANNEL_NAME = "self-promo"
# FILTERED_KEYWORDS are now ignored in channels marked as Age-Restricted/NSFW.
FILTERED_KEYWORDS = ["illegal content", "graphic violence", "shock video", "dtxduo impersonation", "official admin", "mod giveaway"]
SPAM_LINKS = ["bit.ly", "tinyurl", "ow.ly", "shorte.st"]
PROMOTION_KEYWORDS = ["subscribe", "patreon", "youtube", "twitch", "onlyfans", "my channel", "check out my"]
VIBE_RANKS = {"New Neighbor": 0, "Familiar Face": 100, "Resident": 250, "Housemate": 500, "Block Captain": MAX_VIBE_FOR_PRESTIGE}
VIBE_SHOP_ITEMS = {1: {"name": "Icon", "cost": 500, "description": "Icon (Nickname Prefix)"}, 2: {"name": "Flair", "cost": 1000, "description": "Flair (Custom Role)"}}

# --- INTENTS SETUP (CRITICAL!) ---
# Declare all necessary intents, especially the privileged ones
intents = discord.Intents.default()
# Required for Vibe system, user roles, and managing members
intents.members = True          
# CRITICAL for prefix commands (like !say) and on_message filters and DM commands
intents.message_content = True  

# --- BOT INITIALIZATION ---
# Pass the explicit intents to the Bot constructor
bot = commands.Bot(command_prefix='!', intents=intents)

# --- DATABASE / VIBE LOGIC ---
vibe_data = {}
last_vibe_time = {}

def load_data():
    """Loads Vibe data from the JSON file."""
    global vibe_data
    if os.path.exists(DATABASE_FILE) and os.path.getsize(DATABASE_FILE) > 0:
        try:
            with open(DATABASE_FILE, 'r') as f:
                vibe_data = json.load(f)
        except json.JSONDecodeError:
            print("Error loading JSON data. Starting with empty data.")
            vibe_data = {}
    else:
        vibe_data = {}

def save_data(data):
    """Saves Vibe data to the JSON file."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def get_user_data(user_id):
    """Retrieves or initializes user data."""
    user_id = str(user_id)
    if user_id not in vibe_data:
        vibe_data[user_id] = {'vibe': 0, 'last_daily': 0, 'streak': 0, 'rank': 'New Neighbor', 'prestige': 0, 'nickname_icon': '', 'nickname_flair': ''}
    return vibe_data[user_id]

def update_user_rank(user_id, current_vibe):
    """Determines and returns the correct rank name for a given vibe total."""
    current_rank = 'New Neighbor'
    for rank, required_vibe in sorted(VIBE_RANKS.items(), key=lambda item: item[1], reverse=True):
        if current_vibe >= required_vibe:
            current_rank = rank
            break
    return current_rank

async def update_member_roles(member, user_data):
    """Manages cosmetic rank roles (removing old, adding new)."""
    current_rank_name = user_data['rank']
    
    # Check if the member object has a guild (i.e., not a DM interaction)
    if not member.guild: return
    
    # 1. Identify existing rank roles the user has
    all_rank_roles = [r for r in member.roles if r.name in VIBE_RANKS]
    
    # 2. Identify the target role
    target_role = discord.utils.get(member.guild.roles, name=current_rank_name)
    
    if target_role:
        # 3. Remove all old rank roles
        roles_to_remove = [r for r in all_rank_roles if r.name != current_rank_name]
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove, reason="Vibe Rank Change - Removing old rank.")
            
        # 4. Add the new rank role if they don't have it
        if target_role not in member.roles:
            await member.add_roles(target_role, reason="Vibe Rank Change - Granting new rank.")

async def update_nickname_display(member, user_data):
    """Applies icon and flair to the member's nickname."""
    if not member.guild: return # Cannot change nickname in DM

    icon = user_data.get('nickname_icon', '')
    
    # Get the original name (or current nickname if set by another admin)
    original_name = member.name
    
    # Construct the desired nickname format: Icon Name
    new_nickname = f"{icon} {original_name}" if icon else original_name
    
    # Strip leading/trailing spaces and ensure it respects the 32-char limit
    new_nickname = new_nickname.strip()
    if len(new_nickname) > 32:
        # If too long, use only the first 32 characters
        new_nickname = new_nickname[:32]
        
    # Check if the nickname is different and if the bot has permission
    # The bot must have a higher role than the target member to change the nickname.
    if member.nick != new_nickname and member.guild.me.top_role.position > member.top_role.position:
        try:
            # If the new nickname is the same as the user's current server name, set nick to None to clear it.
            if new_nickname == original_name:
                await member.edit(nick=None, reason="Vibe System Nickname Cleared")
            else:
                await member.edit(nick=new_nickname, reason="Vibe System Nickname Update")
        except discord.Forbidden:
            print(f"Failed to change nickname for {member.name} (Missing Permissions or role hierarchy issue).")
    
# --- BOT EVENTS ---

@bot.event
async def on_ready():
    """Confirms bot connection and sets initial status."""
    load_data() # Ensure data is loaded on connection/reconnection
    print(f'🤖 Housemate Ryker is online! Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the block 🏡"))
    
# --- VERIFICATION LISTENER (CRITICAL ROLE) ---
@bot.event
async def on_raw_reaction_add(payload):
    # This fires for all reactions, we only care about the verification message
    if payload.message_id != VERIFICATION_MESSAGE_ID or str(payload.emoji) != VERIFICATION_EMOJI:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild: return
    
    member = guild.get_member(payload.user_id)
    if not member or member.bot: return

    member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
    welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
    
    if member_role and member_role not in member.roles:
        try:
            await member.add_roles(member_role, reason="New Neighbor Verification")
            if welcome_channel:
                await welcome_channel.send(
                    f"**Welcome to the block, {member.mention}!** Verification complete. Check the channels on the left and feel free to introduce yourself."
                )
        except discord.Forbidden:
            print("ERROR: Missing permissions to grant role for verification.")


# --- MESSAGE AND FILTERING HANDLER ---
@bot.event
async def on_message(message):
    # Ignore messages from the bot itself or if it's not a Guild text channel (or a DM command)
    if message.author.bot:
        await bot.process_commands(message)
        return

    # 1. CONTENT FILTERING LOGIC
    # Check if the channel is NOT age-restricted (NSFW) OR if it is a DM.
    is_nsfw_channel = False
    # Only guild text channels have the .is_nsfw() property
    if isinstance(message.channel, discord.TextChannel):
        is_nsfw_channel = message.channel.is_nsfw()
    
    # Flag to check if we should process Vibe/XP
    should_process_vibe = True

    # --- A. Forbidden Keyword Filter (Bypassed if NSFW) ---
    if not is_nsfw_channel and message.guild is not None:
        for keyword in FILTERED_KEYWORDS:
            if keyword.lower() in message.content.lower():
                try:
                    await message.delete()
                    await message.channel.send(f"❌ **REMOVED:** That message violated a content filter. Please review the rules, {message.author.mention}.", delete_after=5)
                    should_process_vibe = False
                    # We must return here to prevent Vibe processing or command processing on a deleted message
                    return
                except discord.Forbidden:
                    print("Error: Missing permissions to delete message for filtering.")
                    
    # --- B. Spam Link Filter ---
    # This filter applies globally (even in NSFW channels) as it prevents external threats/scams
    for link in SPAM_LINKS:
        if link in message.content.lower():
            try:
                if message.guild: await message.delete()
                # Send confirmation privately if it was a guild message
                await message.author.send(f"❌ **REMOVED:** Shortened/suspicious links are not allowed on the block. Your message was removed in {message.channel.name if message.guild else 'DM'}.")
                should_process_vibe = False
                return
            except discord.Forbidden:
                print("Error: Missing permissions to delete message for spam links.")
                
    # --- C. Self-Promotion Warning Filter ---
    if message.guild is not None and message.channel.name != SELF_PROMO_CHANNEL_NAME:
        for keyword in PROMOTION_KEYWORDS:
            if keyword.lower() in message.content.lower():
                # Check for links, as promo keywords alone might be fine
                if any(ext in message.content.lower() for ext in [".com", ".net", "http", "www"]):
                    await message.channel.send(
                        f"⚠️ **Heads Up, {message.author.mention}**: Looks like you're promoting. Please use the **#{SELF_PROMO_CHANNEL_NAME}** channel next time. One-time warning.", 
                        delete_after=10
                    )
                    should_process_vibe = False # Don't give Vibe for promotion warnings
                    # Do NOT return here, let Vibe processing continue if no other filter triggered
                    break # Only send the warning once

    # 2. VIBE/XP LOGIC
    # Only process Vibe if it's a guild message, not a DM, and passed filtering checks
    if message.guild is not None and should_process_vibe:
        user_id = str(message.author.id)
        
        # Check cooldown
        current_time = time.time()
        if user_id in last_vibe_time and (current_time - last_vibe_time[user_id]) < COOLDOWN_SECONDS:
            await bot.process_commands(message)
            return # Too fast, ignore Vibe but process command

        last_vibe_time[user_id] = current_time

        user_data = get_user_data(user_id)
        
        # Grant Vibe
        vibe_earned = random.randint(*VIBE_PER_MESSAGE)
        user_data['vibe'] += vibe_earned
        
        old_rank = user_data['rank']
        new_rank = update_user_rank(user_id, user_data['vibe'])
        user_data['rank'] = new_rank
        
        # Save and process rank change
        if new_rank != old_rank:
            # Announce rank change
            await message.channel.send(f"✨ **LEVEL UP!** {message.author.mention} just hit the **{new_rank}** rank! Keep that Vibe flowing.")
            # Update roles and nickname (if guild is available)
            await update_member_roles(message.author, user_data)
        
        # Check for nickname/icon update
        await update_nickname_display(message.author, user_data)
        
        save_data(vibe_data)

    # 3. COMMAND PROCESSING (Handle commands in Guilds AND DMs)
    await bot.process_commands(message)


# --- VIBE & ECONOMY COMMANDS ---

@bot.command()
async def daily(ctx):
    """Claim your daily Vibe bonus and maintain your streak."""
    user_data = get_user_data(ctx.author.id)
    today = datetime.now().date()
    last_daily_date = datetime.fromtimestamp(user_data['last_daily']).date() if user_data['last_daily'] else None

    if last_daily_date == today:
        # Already claimed today
        await ctx.author.send("⏳ **Hold up!** You've already claimed your daily Vibe today. Check back tomorrow!")
        if ctx.guild: await ctx.message.delete()
        return

    # Check for streak (yesterday's date)
    yesterday = today - discord.utils.DEFAULT_SHARD_ID.timedelta(days=1)
    if last_daily_date == yesterday:
        user_data['streak'] += 1
    else:
        # If it's not today or yesterday, the streak is broken
        if last_daily_date is not None and last_daily_date < yesterday:
             await ctx.author.send(f"💔 **Streak Broken!** You missed a day. Your last streak of **{user_data['streak']} days** has ended.")
        user_data['streak'] = 1
    
    # Calculate bonus
    daily_vibe_bonus = DAILY_VIBE_BASE + (user_data['streak'] * DAILY_VIBE_STREAK_BONUS)
    user_data['vibe'] += daily_vibe_bonus
    user_data['last_daily'] = datetime.now().timestamp()
    
    new_rank = update_user_rank(ctx.author.id, user_data['vibe'])
    user_data['rank'] = new_rank
    
    save_data(vibe_data)
    
    # Check for rank update
    if ctx.guild:
        await update_member_roles(ctx.author, user_data)
        await update_nickname_display(ctx.author, user_data)
        await ctx.message.delete()
    
    # Send confirmation via DM
    embed = discord.Embed(title="☀️ Daily Vibe Claimed", color=discord.Color.green())
    embed.add_field(name="Vibe Earned", value=f"**+{daily_vibe_bonus} Vibe**", inline=True)
    embed.add_field(name="Current Streak", value=f"🔥 **{user_data['streak']} days**", inline=True)
    embed.add_field(name="Total Vibe", value=f"{user_data['vibe']}", inline=True)
    embed.add_field(name="Current Rank", value=f"**{user_data['rank']}**", inline=False)
    
    await ctx.author.send(embed=embed)


@bot.command()
async def rank(ctx):
    """Shows the user's current rank and Vibe progress."""
    user_data = get_user_data(ctx.author.id)
    current_vibe = user_data['vibe']
    current_rank = user_data['rank']
    
    # Find the next rank goal
    next_rank = None
    next_vibe_needed = 0
    
    # Sort ranks by required Vibe and find the next one higher than current
    sorted_ranks = sorted(VIBE_RANKS.items(), key=lambda item: item[1])
    for rank_name, required_vibe in sorted_ranks:
        if required_vibe > current_vibe:
            next_rank = rank_name
            next_vibe_needed = required_vibe - current_vibe
            break
            
    # Prepare output
    title = f"🏡 {ctx.author.display_name}'s Neighborhood Status"
    description = f"**Current Rank:** **{current_rank}**"
    
    if next_rank:
        description += f"\n**Vibe Total:** {current_vibe} Vibe"
        description += f"\n\n**Next Rank ({next_rank}):** Needs **{next_vibe_needed} Vibe** to reach the next tier."
    else:
        description += f"\n**Vibe Total:** {current_vibe} Vibe"
        description += f"\n\n🎉 **You're maxed out!** Type `!prestige` to reset your Vibe and start your Legacy."
        
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    await ctx.send(embed=embed)


@bot.command()
async def profile(ctx):
    """Shows the user's complete Vibe profile."""
    user_data = get_user_data(ctx.author.id)
    
    embed = discord.Embed(title=f"👤 {ctx.author.display_name}'s Vibe Profile", color=discord.Color.purple())
    
    # Main Vibe Stats
    embed.add_field(name="Current Vibe", value=f"**{user_data['vibe']}**", inline=True)
    embed.add_field(name="Daily Streak", value=f"🔥 **{user_data['streak']} days**", inline=True)
    embed.add_field(name="Legacy (Prestige)", value=f"⭐ **{user_data['prestige']}**", inline=True)
    
    # Ranks and Cosmetics
    rank_value = f"**{user_data['rank']}**"
    if user_data.get('nickname_icon') or user_data.get('nickname_flair'):
         rank_value += f" (Cosmetics applied)"

    embed.add_field(name="Neighborhood Rank", value=rank_value, inline=False)
    
    await ctx.send(embed=embed)


@bot.command()
async def leaderboard(ctx):
    """Shows the top 10 members by total Vibe."""
    if not ctx.guild:
        await ctx.author.send("The leaderboard command only works in a server channel.")
        return

    leaderboard_data = {
        member.display_name: data['vibe'] 
        for user_id, data in vibe_data.items() 
        # Only include members still in the guild
        if (member := ctx.guild.get_member(int(user_id))) is not None
    }
    
    if not leaderboard_data:
        await ctx.send("The leaderboard is empty. Start chatting to earn Vibe!")
        return

    # Sort the dictionary items by vibe in descending order
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)

    leaderboard_string = ""
    for i, (name, vibe) in enumerate(sorted_leaderboard[:10]):
        # Use simple bold markdown for ranking
        leaderboard_string += f"**{i+1}.** {name} - {vibe} Vibe\n"

    embed = discord.Embed(
        title="🏆 Top 10 Most Active Neighbors (Vibe Leaderboard)",
        description=leaderboard_string,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)
    
@bot.command()
async def prestige(ctx):
    """Allows the user to reset Vibe for a permanent Legacy boost."""
    user_data = get_user_data(ctx.author.id)
    if user_data['vibe'] < MAX_VIBE_FOR_PRESTIGE:
        vibe_needed = MAX_VIBE_FOR_PRESTIGE - user_data['vibe']
        await ctx.send(f"❌ **HOLD UP:** You need **{vibe_needed} more Vibe** to reach the Block Captain rank before you can enter Legacy (Prestige).")
        return

    # Process Prestige
    user_data['vibe'] = 0
    user_data['prestige'] += 1
    user_data['rank'] = update_user_rank(ctx.author.id, 0) # Reset rank to New Neighbor
    
    save_data(vibe_data)
    
    # Notify user and remove rank roles (they will be added back as they re-rank)
    await ctx.send(f"⭐ **LEGACY INITIATED!** {ctx.author.mention}, you've sacrificed your Vibe to achieve **Legacy Tier {user_data['prestige']}!** Your Vibe is reset, but your status is permanent. Welcome back to the start.")
    
    # Remove all previous rank roles
    if ctx.guild:
        roles_to_remove = [r for r in ctx.author.roles if r.name in VIBE_RANKS]
        if roles_to_remove:
            await ctx.author.remove_roles(*roles_to_remove, reason="Prestige initiated - Rank reset.")


@bot.command()
async def shop(ctx):
    """Displays items available in the Vibe Shop."""
    shop_string = ""
    for item_id, item in VIBE_SHOP_ITEMS.items():
        shop_string += f"**[ID: {item_id}]** **{item['name']}** - {item['cost']} Vibe\n *{item['description']}*\n"
    
    embed = discord.Embed(
        title="🛍️ The Housemate Vibe Shop",
        description=shop_string,
        color=discord.Color.orange()
    )
    embed.set_footer(text="Use !buy [ID] to purchase. Purchases are fulfilled by staff.")
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item_id: int):
    """Purchases an item from the Vibe Shop by ID."""
    if item_id not in VIBE_SHOP_ITEMS:
        await ctx.send("❌ **ERROR:** That item ID doesn't exist in the shop.")
        return
        
    item = VIBE_SHOP_ITEMS[item_id]
    cost = item['cost']
    user_data = get_user_data(ctx.author.id)

    if user_data['vibe'] < cost:
        await ctx.send(f"❌ **NOT ENOUGH VIBE:** You need {cost - user_data['vibe']} more Vibe to buy the **{item['name']}**.")
        return
        
    # Process purchase
    user_data['vibe'] -= cost
    save_data(vibe_data)
    
    # Send confirmation to the user
    await ctx.send(f"✅ **PURCHASE SUCCESSFUL!** Your purchase of **{item['name']}** has been logged. Mods will reach out to fulfill your request soon.")

    # Send detailed alert to mod channel (CRITICAL ALERT)
    mod_channel = bot.get_channel(MOD_ALERTS_CHANNEL_ID)
    if mod_channel:
        fulfillment_instruction = "Manual fulfillment required."
        if item_id == 1:
            fulfillment_instruction = f"Fulfill using: `!set_icon {ctx.author.mention} [icon]`"
        
        alert_embed = discord.Embed(
            title="💰 SHOP PURCHASE ALERT - Action Required",
            description=f"{ctx.author.mention} just bought **{item['name']}** (ID: {item_id}).",
            color=discord.Color.yellow()
        )
        alert_embed.add_field(name="User ID", value=ctx.author.id, inline=False)
        alert_embed.add_field(name="Cost", value=f"{cost} Vibe", inline=True)
        alert_embed.add_field(name="New Vibe Total", value=user_data['vibe'], inline=True)
        alert_embed.add_field(name="Fulfillment Action", value=fulfillment_instruction, inline=False)
        
        await mod_channel.send(embed=alert_embed)

# --- ADMIN UTILITIES ---

@bot.command()
@commands.has_permissions(administrator=True)
async def set_vibe(ctx, member: discord.Member, amount: int):
    """Admin command to manually set a user's Vibe total, updating their rank/roles."""
    user_data = get_user_data(member.id)
    user_data['vibe'] = amount
    
    # Update Rank and Role/Nickname immediately (QoL)
    user_data['rank'] = update_user_rank(member.id, amount)
    save_data(vibe_data)
    
    if ctx.guild:
        await update_member_roles(member, user_data)
        await update_nickname_display(member, user_data)
        
    await ctx.send(f"✅ **Vibe Updated:** Set {member.display_name}'s Vibe to **{amount}**. New Rank: *{user_data['rank']}*")
    
@bot.command()
@commands.has_permissions(administrator=True)
async def update_ranks(ctx, member: discord.Member):
    """Admin command to force a re-check and re-application of a member's rank role and nickname."""
    user_data = get_user_data(member.id)
    
    # Recalculate rank (in case the Vibe Ranks config changed)
    user_data['rank'] = update_user_rank(member.id, user_data['vibe'])
    save_data(vibe_data)

    # Force update roles and nickname
    await update_member_roles(member, user_data)
    await update_nickname_display(member, user_data)

    await ctx.send(f"✅ **Rank Re-Synced:** {member.display_name}'s roles and nickname have been updated according to their Vibe total of **{user_data['vibe']}**.")


@bot.command()
@commands.has_permissions(administrator=True)
async def set_icon(ctx, member: discord.Member, icon: str):
    """Admin command to set a cosmetic icon next to a user's nickname."""
    user_data = get_user_data(member.id)
    # Icon is limited to 2 characters to keep the nickname readable
    user_data['nickname_icon'] = icon[:2] 
    save_data(vibe_data)
    
    # Apply change immediately (QoL)
    if ctx.guild:
        await update_nickname_display(member, user_data)

    await ctx.send(f"✅ **Icon Updated:** Set icon for {member.display_name} to: {icon}")

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, channel: discord.TextChannel, *, message: str):
    """Admin command to make the bot send a message to a specific channel."""
    try: 
        await channel.send(message) 
        await ctx.message.delete()
    except Exception as e: 
        await ctx.send(f"❌ Could not post message to {channel.mention}. Error: {e}")

# --- COMMUNITY UTILITIES ---

@bot.command()
async def report(ctx, member: discord.Member, *, reason: str):
    """
    Sends a confidential report about a user to the Mod Alerts channel.
    Works in DMs for private reporting (anonymous).
    """
    # Fetch mod channel globally since ctx.guild might be None (DM)
    mod_channel = bot.get_channel(MOD_ALERTS_CHANNEL_ID)
    
    is_dm = ctx.guild is None
    
    # Determine the reporter context
    reporter_mention = ctx.author.mention
    source_channel = ctx.channel.mention
    
    if is_dm:
        # If reporting from a private DM, the reporter is anonymized
        reporter_mention = f"**Private DM Reporter** (ID: {ctx.author.id})"
        source_channel = "Direct Message (Private Report)"
    elif ctx.channel.name.lower() == "mod-mail" or "private-report":
        # If reporting in a known private channel, keep it semi-anonymous
        reporter_mention = f"**{ctx.author.display_name}** (Private Channel)"


    if mod_channel:
        embed = discord.Embed(title="⚠️ USER REPORT - CRITICAL ALERT", color=discord.Color.red())
        embed.add_field(name="Reported User", value=member.mention, inline=True)
        embed.add_field(name="Reported By", value=reporter_mention, inline=True)
        embed.add_field(name="Source Channel", value=source_channel, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await mod_channel.send(embed=embed)
        
        # Only delete the command message if it was sent in a server channel (not DM)
        if not is_dm:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                print("Could not delete report message (Missing Permissions).")
                
        # Send confirmation to the reporter (works in DM or Guild)
        await ctx.author.send(
            f"✅ Your confidential report against **{member.display_name}** has been sent to the Mod team. Thank you for keeping the block safe."
        )
    else:
        # Fallback if mod channel ID is incorrect
        await ctx.author.send(f"❌ ERROR: Could not find the Mod Alerts Channel (ID: {MOD_ALERTS_CHANNEL_ID}). Please contact an admin directly.")


# --- GLOBAL COMMAND ERROR HANDLER ---
@bot.event
async def on_command_error(ctx, error):
    # This prevents handling errors at the command level if they are ignored
    if hasattr(ctx.command, 'on_error'):
        return

    # Ignore command not found errors (keeps bot logs cleaner from typos)
    if isinstance(error, commands.CommandNotFound):
        return

    # User Permission Check Failure
    if isinstance(error, commands.MissingPermissions):
        missing = [p.replace('_', ' ').title() for p in error.missing_permissions]
        await ctx.send(f"❌ **User Error:** You need the following permission(s) to use this command: **{', '.join(missing)}**")
        return

    # Bot Permission Check Failure
    if isinstance(error, commands.BotMissingPermissions):
        missing = [p.replace('_', ' ').title() for p in error.missing_permissions]
        await ctx.send(f"⚠️ **Bot Error:** I am missing the following permission(s) to run this command: **{', '.join(missing)}**. Please check my role hierarchy and permissions.")
        return
        
    # Argument conversion error (e.g., providing text for an int field)
    if isinstance(error, commands.BadArgument):
         await ctx.send(f"❌ **Input Error:** I couldn't understand one of your inputs. Please check the command syntax and try again.")
         return
         
    # Handle other errors (like the user not being found for !report)
    print(f"Unhandled command error in {ctx.command}: {error}")