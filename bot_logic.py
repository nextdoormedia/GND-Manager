import discord
from discord.ext import commands
from datetime import datetime
import json
import asyncio
from typing import Union

# --- CONFIGURATION CONSTANTS ---
WELCOME_CHANNEL_ID = 1420121916404007136
VERIFICATION_MESSAGE_ID = 1420121916404007137
VERIFICATION_EMOJI = "✅"
MEMBER_ROLE_NAME = "Member"
MOD_ALERTS_CHANNEL_ID = 1420127688248660081
MUTED_ROLE_NAME = "Muted"
SELF_PROMO_CHANNEL_NAME = "self-promo"
MOD_LOG_FILE = 'mod_logs.json' 
mod_db = {} 

# Filtering lists (Kept concise)
FILTERED_KEYWORDS = ["illegal content", "graphic violence", "shock video", "dtxduo impersonation", "official admin", "mod giveaway"]
SPAM_LINKS = ["bit.ly", "tinyurl", "ow.ly", "shorte.st"]
PROMOTION_KEYWORDS = ["subscribe", "patreon", "youtube", "twitch", "onlyfans", "my channel", "check out my"]

# --- INTENTS & BOT INITIALIZATION ---
intents = discord.Intents.default()
intents.members = True          
intents.message_content = True  
bot = commands.Bot(command_prefix='!', intents=intents)


# --- DATABASE HELPER FUNCTIONS (Essential for persistence) ---

def load_db():
    """Loads the moderation log database from the JSON file."""
    global mod_db
    try:
        with open(MOD_LOG_FILE, 'r') as f:
            mod_db = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"INFO: Starting new mod log database. Reason: {e}")
        mod_db = {}

def save_db():
    """Saves the in-memory moderation log database to the JSON file."""
    with open(MOD_LOG_FILE, 'w') as f:
        json.dump(mod_db, f, indent=4)

async def log_action(user_id: int, action: str, moderator_id: int, reason: str):
    """Logs an administrative action and saves it to disk."""
    user_id_str = str(user_id)
    entry = {
        "action": action,
        "moderator_id": str(moderator_id),
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
        "reason": reason
    }
    
    if user_id_str not in mod_db:
        mod_db[user_id_str] = []
    
    mod_db[user_id_str].append(entry)
    await bot.loop.run_in_executor(None, save_db)


# --- GENERAL HELPER FUNCTIONS ---

async def send_mod_alert_embed(guild, title, description, color=discord.Color.yellow()):
    """Helper to send a custom embed to the Mod Alerts Channel."""
    mod_channel = guild.get_channel(MOD_ALERTS_CHANNEL_ID)
    if not mod_channel: 
        print("WARNING: Mod Alerts Channel not found.")
        return

    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"Alert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        await mod_channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending mod alert: {e}")

def get_role_by_name(guild: discord.Guild, name: str) -> Union[discord.Role, None]:
    """Retrieves a role object by name."""
    return discord.utils.get(guild.roles, name=name)


# --- BOT EVENTS ---

@bot.event
async def on_ready():
    """Confirms bot ready, loads database, sets activity."""
    load_db()
    print(f'✅ Housemate Ryker (Security Focus) is logged in as {bot.user}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the Neighborhood Security"))

@bot.event
async def on_member_join(member):
    """Handles welcome, mod alert, and ban evasion enforcement."""
    guild = member.guild
    user_id_str = str(member.id)

    # DB Enforcement Check for Ban Evasion
    if user_id_str in mod_db:
        # Find the most recent, permanent BAN action
        recent_ban = next((log for log in reversed(mod_db[user_id_str]) if log['action'] == 'BAN'), None)

        if recent_ban:
            reason = recent_ban['reason']
            try:
                await guild.ban(member, reason=f"Automatic re-ban (DB enforcement). Original Reason: {reason}")
                await send_mod_alert_embed(
                    guild, "🚨 RE-BAN ENFORCED (DB Match)",
                    f"**User:** {member.mention} (`{member.id}`) was auto-banned.\n**Original Reason:** {reason}",
                    discord.Color.dark_red()
                )
                return 

    # Normal Welcome
    welcome_channel = guild.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        await welcome_channel.send(f"Welcome to the Neighborhood, {member.mention}! Please verify.")
        
    await send_mod_alert_embed(
        guild, "🚪 NEW NEIGHBOR ARRIVED", 
        f"**User:** {member.mention}\n**ID:** `{member.id}`\n**Created:** {member.created_at.strftime('%Y-%m-%d')}",
        discord.Color.blue()
    )

@bot.event
async def on_member_remove(member):
    """Alerts mods when a member leaves."""
    await send_mod_alert_embed(
        member.guild, "🚪 NEIGHBOR REMOVED/LEFT",
        f"**{member.display_name}** (`{member.id}`) has left the server.",
        discord.Color.red()
    )


# --- VERIFICATION SYSTEM ---

@bot.event
async def on_raw_reaction_add(payload):
    """Handles reaction-based verification."""
    if payload.message_id != VERIFICATION_MESSAGE_ID or str(payload.emoji) != VERIFICATION_EMOJI:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id)
    if not member or member.bot: return

    member_role = get_role_by_name(guild, MEMBER_ROLE_NAME)
    
    if member_role and member_role not in member.roles:
        try:
            await member.add_roles(member_role)
            await send_mod_alert_embed(
                guild, "✅ MEMBER VERIFIED (Reaction)", 
                f"{member.mention} was granted the **{MEMBER_ROLE_NAME}** role.",
                discord.Color.green()
            )
        except Exception as e:
            print(f"ERROR: Could not grant role to {member.display_name}: {e}")

@bot.command()
async def verify(ctx):
    """Allows users to verify using a command."""
    member_role = get_role_by_name(ctx.guild, MEMBER_ROLE_NAME)
    member = ctx.author
    
    if not member_role:
        return await ctx.send("❌ Error: The Member role is not set up correctly.")
    if member_role in member.roles:
        await ctx.message.delete()
        return await ctx.send("✅ You are already a verified Neighbor!", delete_after=5)

    try:
        await member.add_roles(member_role)
        await ctx.send(f"✅ Welcome to the neighborhood, {member.mention}! You are now verified.", delete_after=5)
        await ctx.message.delete()
        await send_mod_alert_embed(
            ctx.guild, "✅ MEMBER VERIFIED (Command)", 
            f"{member.mention} has self-verified using `!verify`.",
            discord.Color.green()
        )
    except Exception:
        await ctx.send("❌ Error: I couldn't grant the role. Check permissions.", delete_after=5)


# --- MESSAGE FILTERING ---

@bot.event
async def on_message(message):
    """Runs filters and processes commands."""
    if message.author.bot:
        return

    content = message.content.lower()
    channel_name = message.channel.name

    # 1. Spam Link Filter
    if any(link in content for link in SPAM_LINKS):
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, abbreviated spam links are prohibited.", delete_after=5)
        await send_mod_alert_embed(message.guild, "🛑 SPAM LINK DELETED", f"**User:** {message.author.display_name}\n**Channel:** {message.channel.mention}", discord.Color.dark_red())
        return

    # 2. Forbidden Keyword Filter (Skips NSFW)
    if not message.channel.is_nsfw() and any(keyword in content for keyword in FILTERED_KEYWORDS):
        await message.delete()
        await message.channel.send(f"🛑 {message.author.mention}, that content is prohibited.", delete_after=5)
        await send_mod_alert_embed(message.guild, "🛑 FORBIDDEN KEYWORD DELETED", f"**User:** {message.author.display_name}\n**Channel:** {message.channel.mention}", discord.Color.dark_red())
        return

    # 3. Self-Promotion Control
    if channel_name != SELF_PROMO_CHANNEL_NAME and any(promo_word in content for promo_word in PROMOTION_KEYWORDS):
        await message.channel.send(f"📣 {message.author.mention}, please use the **#{SELF_PROMO_CHANNEL_NAME}** channel for promotion.", delete_after=10)
        await send_mod_alert_embed(message.guild, "⚠️ PROMO WARNING ISSUED", f"**User:** {message.author.display_name} in {message.channel.mention}", discord.Color.yellow())

    # Process commands
    await bot.process_commands(message)


# --- UTILITY COMMANDS (DB Integrated) ---

@bot.command(aliases=['user', 'memberinfo'])
@commands.has_permissions(kick_members=True)
async def whois(ctx, member: discord.Member = None):
    """Provides detailed security information and mod history about a user."""
    member = member or ctx.author
    roles = [role.name for role in member.roles if role.name != "@everyone"]
    
    # DB Lookup
    history = mod_db.get(str(member.id), [])
    
    # Moderation History Formatting (last 3 actions)
    history_text = "No disciplinary actions recorded."
    if history:
        latest_actions = history[-3:]
        history_text = "\n".join([
            f"`{entry['timestamp'][:10]}`: **{entry['action']}** by <@{entry['moderator_id']}> - *{entry['reason'][:75]}...*"
            for entry in latest_actions
        ])
        if len(history) > 3:
            history_text += f"\n\n*...and {len(history) - 3} more actions logged.*"
    
    # Build Embed
    embed = discord.Embed(
        title=f"Security Profile: {member.display_name}",
        color=member.color if member.color != discord.Color.default() else discord.Color.dark_grey()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="User ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M UTC") if member.joined_at else "N/A", inline=False)
    embed.add_field(name="Roles", value=", ".join(roles) if roles else "No custom roles.", inline=False)
    embed.add_field(name="🚨 Moderation History", value=history_text, inline=False)
        
    await ctx.send(embed=embed)

@bot.command()
async def report(ctx, member: discord.Member, *, reason: str):
    """Allows a user to privately report another member."""
    # Log the report action to the database
    await log_action(member.id, "REPORTED", ctx.author.id, reason)
    
    # Send Mod Alert
    embed = discord.Embed(title="⚠️ USER REPORT", description="A member has submitted a private report.", color=discord.Color.red())
    embed.add_field(name="Reported User", value=f"{member.mention} (`{member.id}`)", inline=False)
    embed.add_field(name="Reported By", value=ctx.author.mention, inline=False)
    embed.add_field(name="Reason", value=reason, inline=False)
    
    mod_channel = ctx.guild.get_channel(MOD_ALERTS_CHANNEL_ID)
    if mod_channel: await mod_channel.send(embed=embed)

    await ctx.message.delete()
    try:
        await ctx.author.send(f"✅ Your report against {member.display_name} has been securely sent to the moderation team.")
    except:
        await ctx.send(f"✅ Report submitted (could not send DM confirmation).", delete_after=5)


# --- ADMIN COMMANDS (DB Logging) ---

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kicks a member and logs the action."""
    if member == ctx.author or member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send("❌ Cannot kick this member due to role hierarchy or self-targeting.")
        
    await member.kick(reason=reason)
    await log_action(member.id, "KICK", ctx.author.id, reason)
    await ctx.send(f"✅ **{member.display_name}** has been kicked. Reason: *{reason}*")
    await send_mod_alert_embed(
        ctx.guild, "🥾 MEMBER KICKED",
        f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
        discord.Color.orange()
    )


@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    """Bans a member, logs the action, and enables auto-enforcement."""
    if member == ctx.author or member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send("❌ Cannot ban this member due to role hierarchy or self-targeting.")

    await member.ban(reason=reason)
    await log_action(member.id, "BAN", ctx.author.id, reason)
    await ctx.send(f"✅ **{member.display_name}** has been permanently evicted. Reason: *{reason}*")
    await send_mod_alert_embed(
        ctx.guild, "🔨 MEMBER BANNED (Permanent)",
        f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
        discord.Color.dark_red()
    )


@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason="No reason provided"):
    """Mutes a member and logs the action."""
    muted_role = get_role_by_name(ctx.guild, MUTED_ROLE_NAME)
    
    if not muted_role:
        return await ctx.send(f"❌ Error: Role **{MUTED_ROLE_NAME}** not found.")
    if muted_role in member.roles:
        return await ctx.send(f"⚠️ **{member.display_name}** is already muted.")

    await member.add_roles(muted_role, reason=reason)
    await log_action(member.id, "MUTE", ctx.author.id, reason)
    await ctx.send(f"🔇 **{member.display_name}** has been muted. Reason: *{reason}*")
    await send_mod_alert_embed(
        ctx.guild, "🔇 MEMBER MUTED",
        f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
        discord.Color.red()
    )


@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member, *, reason="Mute period over"):
    """Unmutes a member and logs the action."""
    muted_role = get_role_by_name(ctx.guild, MUTED_ROLE_NAME)

    if not muted_role:
        return await ctx.send(f"❌ Error: Role **{MUTED_ROLE_NAME}** not found.")
    if muted_role not in member.roles:
        return await ctx.send(f"⚠️ **{member.display_name}** is not currently muted.")

    await member.remove_roles(muted_role, reason=reason)
    await log_action(member.id, "UNMUTE", ctx.author.id, reason)
    await ctx.send(f"🔊 **{member.display_name}** has been unmuted.")
    await send_mod_alert_embed(
        ctx.guild, "🔊 MEMBER UNMUTED",
        f"**User:** {member.mention}\n**Moderator:** {ctx.author.mention}\n**Reason:** {reason}",
        discord.Color.green()
    )


@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    """Deletes a specified number of messages."""
    if amount < 1:
        return await ctx.send("❌ Amount must be at least 1.")

    deleted = await ctx.channel.purge(limit=amount + 1)
    await log_action(ctx.channel.id, "PURGE", ctx.author.id, f"{len(deleted)-1} messages deleted in {ctx.channel.name}")
    
    await ctx.send(f"🗑️ Deleted **{len(deleted)-1}** messages.", delete_after=5)
    await send_mod_alert_embed(
        ctx.guild, "🗑️ MESSAGES PURGED",
        f"**Channel:** {ctx.channel.mention}\n**Moderator:** {ctx.author.mention}\n**Amount:** {len(deleted)-1}",
        discord.Color.dark_grey()
    )


# --- HELP MENU ---

@bot.command()
async def helpme(ctx):
    """Provides a list of the core remaining commands."""
    embed = discord.Embed(
        title="🏠 Housemate Ryker: Security & Moderation",
        description="Ryker focuses on security, accountability, and administration.",
        color=discord.Color.dark_teal()
    )
    
    embed.add_field(name="🌐 Public Commands", value="---", inline=False)
    embed.add_field(name="!verify", value="Grants the Member role.", inline=True)
    embed.add_field(name="!report @user [reason]", value="Privately alerts mods (action is logged).", inline=True)
    
    embed.add_field(name="🚨 Moderation Commands", value="---", inline=False)
    embed.add_field(name="!whois (@user)", value="User info and **Moderation History**.", inline=True)
    embed.add_field(name="!purge [amount]", value="Deletes messages.", inline=True)
    embed.add_field(name="!kick / !ban", value="Removes/Evicts members (logged & auto-enforced).", inline=True)
    embed.add_field(name="!mute / !unmute", value="Manages the Muted role (logged).", inline=True)
    
    embed.set_footer(text="All disciplinary actions are permanently logged to mod_logs.json for accountability.")
    await ctx.send(embed=embed)


# --- GLOBAL COMMAND ERROR HANDLER (Kept robust) ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ **Syntax Error:** Missing argument(s). Use `!helpme` for correct usage.")
        return
    if isinstance(error, commands.MissingPermissions):
        missing = [p.replace('_', ' ').title() for p in error.missing_permissions]
        await ctx.send(f"❌ **User Error:** You need permission(s): **{', '.join(missing)}**")
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send("❌ **Input Error:** Could not find the specified user or invalid input type.")
        return
        
    print(f"Unhandled command error in {ctx.command}: {error}")
    await ctx.send("💥 An unexpected error occurred while processing the command.")
