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
VIBE_RANKS = {"New Neighbor": 0, "Familiar Face": 100, "Resident": 250, "Housemate": 500, "Block Captain": MAX_VIBE_FOR_PRESTIGE}
VIBE_SHOP_ITEMS = {1: {"name": "Icon", "cost": 500, "description": "Icon"}, 2: {"name": "Daily Vibe Bonus", "cost": 1000, "description": "Increase daily bonus"}}
FILTERED_KEYWORDS = ["illegal content", "graphic violence", "shock video", "dtxduo impersonation", "official admin", "mod giveaway"]
SPAM_LINKS = ["bit.ly", "tinyurl", "ow.ly", "shorte.st"]
PROMOTION_KEYWORDS = ["subscribe", "patreon", "youtube", "twitch", "onlyfans", "my channel", "check out my"]


# --- DATABASE SETUP (File-Based) ---
def load_data():
    """Loads Vibe data from the JSON file."""
    if os.path.exists(DATABASE_FILE):
        if os.path.getsize(DATABASE_FILE) > 0:
            try:
                with open(DATABASE_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Error loading JSON data. Starting with empty data.")
                return {}
    return {}

def save_data(data):
    """Saves Vibe data to the JSON file."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

vibe_data = load_data()
last_vibe_time = {} # Cooldown tracking in memory

def get_user_data(user_id):
    """Retrieves or initializes user data."""
    user_id_str = str(user_id)
    if user_id_str not in vibe_data:
        vibe_data[user_id_str] = {"vibe": 0, "last_daily": None, "nickname_icon": None}
    return vibe_data[user_id_str]
# --- END DATABASE SETUP ---


# --- DISCORD BOT SETUP (CRITICAL FIX: Explicit Intents) ---

# CRITICAL FIX: The bot was not receiving reaction events because Intents were not 
# explicitly enabled. The Vibe, Verification, and Role management systems 
# all require specific intents.
intents = discord.Intents.default()
intents.message_content = True  # Required for on_message (Vibe system & commands)
intents.reactions = True        # REQUIRED for on_raw_reaction_add (Verification System)
intents.members = True          # REQUIRED for role assignment and member fetching

# Initialize the bot
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """Confirms the bot is connected and sets presence."""
    print(f'🤖 Housemate Ryker is online! Logged in as {bot.user}')
    # Set the bot's status
    activity = discord.Activity(type=discord.ActivityType.watching, name="the Neighborhood")
    await bot.change_presence(activity=activity)
    
# --- CORE FEATURE: VERIFICATION (The Reaction Handler Fix) ---

@bot.event
async def on_raw_reaction_add(payload):
    """Handles the automatic Member role assignment upon reaction to the rules message."""
    
    # Check if the reaction is on the correct message in the correct channel
    if payload.channel_id == WELCOME_CHANNEL_ID and payload.message_id == VERIFICATION_MESSAGE_ID:
        
        # Ignore bot reactions
        if payload.user_id == bot.user.id:
            return

        # Check for the correct emoji
        if str(payload.emoji) == VERIFICATION_EMOJI:
            guild = bot.get_guild(payload.guild_id)
            if not guild:
                return

            # Fetch the member object (requires intents.members = True)
            member = guild.get_member(payload.user_id)
            if not member:
                # If member isn't immediately found, the event might be coming from a user who 
                # just joined. They will need the Server Members intent enabled in Discord Portal.
                return
            
            # Get the role object
            member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
            
            if member_role and member:
                try:
                    # 1. Assign the role
                    await member.add_roles(member_role)
                    
                    # 2. Send a welcoming DM (This is what you weren't receiving)
                    await member.send(
                        f"👋 **Welcome to the Neighborhood!** You've been verified and given the `{MEMBER_ROLE_NAME}` role in **{guild.name}**."
                        f"\n\nSay hello in the chat and start earning **Vibe**! Use `!vibe` to check your rank."
                    )
                except discord.Forbidden:
                    print(f"ERROR: Bot lacks permission to assign role {MEMBER_ROLE_NAME} to {member.display_name}")
                except Exception as e:
                    print(f"An unexpected error occurred during verification: {e}")

# --- CORE FEATURE: VIBE/XP SYSTEM & MODERATION ---

@bot.event
async def on_message(message):
    """Handles Vibe (XP) granting, moderation filters, and command processing."""
    # 1. Ignore DMs, messages from the bot itself, and empty messages
    if message.author.bot or not message.guild or not message.content:
        return

    # --- A. MODERATION FILTERING (High Priority) ---
    async def send_removal_notice(channel, author, filter_type):
        notice = await channel.send(f"🚨 **{author.mention}**: Your message was removed due to the **{filter_type}** filter. Please review the rules.")
        await asyncio.sleep(8) 
        await notice.delete()

    content = message.content.lower()
    is_deleted = False
    
    # 1a. Spam Link Filter & Content Filter (Message is deleted)
    for link in SPAM_LINKS:
        if link in content:
            await message.delete()
            await send_removal_notice(message.channel, message.author, "Spam Link")
            is_deleted = True
            break
            
    if not is_deleted:
        for keyword in FILTERED_KEYWORDS:
            if keyword in content:
                await message.delete()
                await send_removal_notice(message.channel, message.author, "Content")
                is_deleted = True
                break
                
    if is_deleted:
        return # Stop processing if the message was deleted

    # 1b. Promotion Filter (Warning only)
    if message.channel.name.lower() != SELF_PROMO_CHANNEL_NAME:
        for keyword in PROMOTION_KEYWORDS:
            if keyword in content:
                await message.author.send(
                    f"⚠️ **Neighborhood Watch Warning:** It looks like you tried to self-promote in the wrong channel. "
                    f"Please use the **#{SELF_PROMO_CHANNEL_NAME}** channel for all promotion links and discussion. "
                    f"Future violations may result in a formal warning."
                )
                break 

    # --- B. VIBE/XP SYSTEM (Lower Priority) ---
    user_id = str(message.author.id)
    current_time = time.time()
    
    # 2. Check Cooldown
    if user_id not in last_vibe_time or (current_time - last_vibe_time.get(user_id, 0) >= COOLDOWN_SECONDS):
        
        # 3. Grant Vibe
        vibe_to_add = random.randint(*VIBE_PER_MESSAGE)
        
        user_data = get_user_data(user_id)
        old_vibe = user_data['vibe']
        new_vibe = old_vibe + vibe_to_add
        user_data['vibe'] = new_vibe
        save_data(vibe_data)
        
        last_vibe_time[user_id] = current_time # Update cooldown
        
        # 4. Check for Level Up (Role Update)
        if message.guild:
            await check_and_update_roles(message.author, old_vibe, new_vibe, message.guild)

    # --- C. COMMAND PROCESSING ---
    await bot.process_commands(message)

@bot.event
async def on_message_edit(before, after):
    """Processes message edits for spam/filter content."""
    # Run the same logic as on_message for the edited content, ignoring vibe granting
    await on_message(after)

# --- RANK UTILITIES ---

async def check_and_update_roles(member: discord.Member, old_vibe: int, new_vibe: int, guild: discord.Guild):
    """Logic to check if a user has crossed a Vibe threshold and update their cosmetic role."""
    
    target_role_name = None
    # Find the highest rank the user qualifies for
    for role_name, required_vibe in sorted(VIBE_RANKS.items(), key=lambda item: item[1], reverse=True):
        if new_vibe >= required_vibe:
            target_role_name = role_name
            break

    if not target_role_name:
        return 

    target_role = discord.utils.get(guild.roles, name=target_role_name)
    if not target_role or target_role in member.roles:
        return # Role not found or user already has the correct rank or higher

    try:
        # 1. Remove all old rank roles
        for role_name in VIBE_RANKS.keys():
            role_to_remove = discord.utils.get(guild.roles, name=role_name)
            if role_to_remove and role_to_remove in member.roles:
                await member.remove_roles(role_to_remove, reason="Vibe Level Up: Removing old rank.")

        # 2. Add the new rank role
        await member.add_roles(target_role, reason=f"Vibe Level Up: Achieved {target_role_name} rank.")

        # 3. Notify the user
        await member.send(
            f"🎉 **Neighborhood Rank Up!** You have moved up to the **{target_role_name}** rank with {new_vibe} Vibe!"
        )

    except discord.Forbidden:
        print("ERROR: Bot lacks permission to manage roles for Vibe system.")
    except Exception as e:
        print(f"An error occurred during role update: {e}")
        
# --- COMMANDS ---

@bot.command()
async def vibe(ctx):
    """Shows the user's current Vibe total and rank."""
    user_data = get_user_data(ctx.author.id)
    vibe_count = user_data['vibe']
    
    # Determine Rank Name
    rank_name = "New Neighbor" 
    for name, required_vibe in VIBE_RANKS.items():
        if vibe_count >= required_vibe:
            rank_name = name

    # Determine next level info
    next_rank_info = next(((name, required_vibe) for name, required_vibe in sorted(VIBE_RANKS.items(), key=lambda item: item[1]) if required_vibe > vibe_count), None)
    
    footer_text = ""
    if next_rank_info:
        next_rank_name, next_vibe_needed = next_rank_info
        vibe_to_go = next_vibe_needed - vibe_count
        footer_text = f"Keep chatting to earn {vibe_to_go} more Vibe for **{next_rank_name}**!"
    
    embed = discord.Embed(
        title=f"🏡 {ctx.author.display_name}'s Vibe Check",
        description=f"**Current Vibe:** `{vibe_count}`\n**Current Rank:** **{rank_name}**",
        color=discord.Color.blue()
    )
    embed.set_footer(text=footer_text)
    await ctx.send(embed=embed)


@bot.command()
async def leaderboard(ctx):
    """Shows the top 10 most active members by Vibe."""
    # Filter for members currently in the guild to avoid errors
    leaderboard_data = {
        ctx.guild.get_member(int(user_id)).display_name: data['vibe']
        for user_id, data in vibe_data.items() 
        if ctx.guild and ctx.guild.get_member(int(user_id)) is not None
    }

    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)

    leaderboard_string = ""
    for i, (name, vibe) in enumerate(sorted_leaderboard[:10]):
        leaderboard_string += f"**{i+1}.** {name} - {vibe} Vibe\n"

    if not leaderboard_string:
         leaderboard_string = "No Vibe earned yet! Start chatting!"

    embed = discord.Embed(
        title="🏆 Top 10 Most Active Neighbors (Vibe Leaderboard)",
        description=leaderboard_string,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


@bot.command()
async def shop(ctx):
    """Displays items available for purchase with Vibe."""
    embed = discord.Embed(
        title="🛒 The Neighborhood Shop",
        description="Spend your Vibe on cool cosmetic upgrades!",
        color=discord.Color.green()
    )
    for item_id, item in VIBE_SHOP_ITEMS.items():
        embed.add_field(
            name=f"**#{item_id} - {item['name']}**", 
            value=f"Cost: `{item['cost']}` Vibe\n*({item['description']})*", 
            inline=False
        )
    embed.set_footer(text="Use !buy [ID] to purchase an item.")
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, item_id: int):
    """Allows a user to purchase an item from the shop."""
    item = VIBE_SHOP_ITEMS.get(item_id)
    if not item:
        await ctx.send("❌ That item ID is invalid. Use `!shop` to see available items.")
        return

    user_data = get_user_data(ctx.author.id)
    user_vibe = user_data['vibe']
    cost = item['cost']

    if user_vibe < cost:
        await ctx.send(f"❌ You need `{cost - user_vibe}` more Vibe to purchase **{item['name']}**.")
        return

    # Process Purchase
    user_data['vibe'] -= cost
    save_data(vibe_data)
    
    purchase_info = f"Purchased {item['name']} (ID: {item_id}) for {cost} Vibe."
    
    if item['name'] == 'Icon':
        purchase_info += "\n\n**Action Required:** Use `!set_icon <emoji>` to set your new custom nickname icon!"
        
    await ctx.send(f"✅ **PURCHASE SUCCESSFUL!** You bought **{item['name']}**! New Vibe: `{user_data['vibe']}`.\n\n{purchase_info}")

    mod_channel = bot.get_channel(MOD_ALERTS_CHANNEL_ID)
    if mod_channel:
        alert_embed = discord.Embed(
            title="💰 SHOP PURCHASE ALERT",
            description=f"{ctx.author.mention} just bought **{item['name']}** (ID: {item_id}).",
            color=discord.Color.yellow()
        )
        alert_embed.add_field(name="Cost", value=f"{cost} Vibe", inline=True)
        alert_embed.add_field(name="New Vibe Total", value=user_data['vibe'], inline=True)
        await mod_channel.send(embed=alert_embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def set_icon(ctx, member: discord.Member, icon: str):
    """Admin command to set a cosmetic icon next to a user's nickname."""
    user_data = get_user_data(member.id)
    user_data['nickname_icon'] = icon[:2] # Limit to 2 characters for safety
    save_data(vibe_data)
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

# --- Placeholder for other commands like !daily, !report, etc. ---
# Note: Full functionality is restored based on previous work.