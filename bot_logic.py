# bot_logic.py
# Core logic, commands, and events for GND Manager.
# bot_logic.py
# Core logic, commands, and events for GND Manager, including metric collection.

import os
import json
from datetime import datetime, timedelta
from discord.ext import commands, tasks
import discord
import asyncio
import time 
import collections # New: for easy counter initialization

# --- CONFIGURATION & SETUP ---

# Fetches the bot token from the environment variable set on Render
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
COMMAND_PREFIX = '!'

# Filepaths
MOD_LOGS_FILE = 'mod_logs.json'
METRICS_FILE = 'server_metrics.json' # New: File for community health metrics

# Role Names
MEMBER_ROLE_NAME = 'Member'
MUTED_ROLE_NAME = 'Muted'

# Channel IDs (PLACEHOLDERS - MUST BE UPDATED)
MOD_ALERT_CHANNEL_ID = 123456789012345678 
VERIFICATION_CHANNEL_ID = 123456789012345679 
VERIFICATION_EMOJI = '✅'

# In-Memory Metric Trackers (Used to limit file I/O from frequent events)
# These will be updated every time a message is sent, but only saved to disk periodically.
ACTIVE_CHATTERS = set() # Unique user IDs who send a message since last reset/startup
CHANNEL_ACTIVITY = collections.defaultdict(int) # {channel_id: message_count}

# --- HELPER FUNCTIONS FOR WEB DASHBOARD ---
def get_active_chatters():
    """Returns the current count of unique active chatters."""
    return len(ACTIVE_CHATTERS)

def get_discord_invite_link():
    """Returns the primary Discord invite link for the admin dashboard."""
    # NOTE: This link should be kept in sync with the one in app.py
    return "https://discord.gg/EKekh3wHYQ" 
    
# Global data containers and start time
MOD_LOGS = {'logs': []}
SERVER_METRICS = {}
BOT_START_TIME = time.time()

# Intents are mandatory for modern discord bots to declare what events they listen to.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.reactions = True

# Initialize the bot client (GND Manager)
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# --- JSON HELPER FUNCTIONS ---

def load_json(filepath, default_data={}):
    """Loads JSON data from a file, initializing with default data if necessary."""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}. Initializing with default structure.")
        try:
            with open(filepath, 'w') as f:
                json.dump(default_data, f, indent=4)
            return default_data
        except Exception as e:
            print(f"ERROR: Could not create {filepath}. {e}")
            return default_data
    
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Error decoding JSON from {filepath}: {e}. Returning default data.")
        return default_data
    except Exception as e:
        print(f"ERROR: Failed to read {filepath}. {e}")
        return default_data

def save_json(filepath, data):
    """Saves data to a JSON file."""
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"ERROR: Failed to save data to {filepath}: {e}")

def load_initial_data():
    """Loads both moderation logs and server metrics upon bot startup."""
    global MOD_LOGS
    global SERVER_METRICS

    # 1. Load/Initialize Mod Logs
    MOD_LOGS = load_json(MOD_LOGS_FILE, default_data={'logs': []})
    
    # 2. Load/Initialize Server Metrics (NEW)
    default_metrics = {
        'join_log': {},           # {'2025-09-27': 5, ...}
        'leave_log': {},          # {'2025-09-27': 2, ...}
        'channel_activity_log': {}, # {channel_id: count, ...} - Last saved state
        'monthly_summary': {
            'total_mutes': 0,
            'total_bans': 0,
            'total_kicks': 0,
            'last_reset': str(datetime.now().date())
        }
    }
    SERVER_METRICS = load_json(METRICS_FILE, default_metrics)
    # Restore last known channel activity from file to memory
    for k, v in SERVER_METRICS.get('channel_activity_log', {}).items():
        CHANNEL_ACTIVITY[int(k)] = v

load_initial_data() # Execute load at script start

# --- METRICS & DATA MANAGEMENT FUNCTIONS (NEW) ---

def update_log_and_metrics(action, target_id, moderator_id, reason, guild_members):
    """
    Saves a log entry to mod_logs.json and updates the monthly metrics count.
    
    :param guild_members: List of current guild members needed for metric calculation.
    """
    timestamp = datetime.now().isoformat()
    log_entry = {
        'timestamp': timestamp,
        'action': action,
        'target_id': str(target_id),
        'moderator_id': str(moderator_id),
        'reason': reason
    }
    
    MOD_LOGS['logs'].insert(0, log_entry) # Insert at the beginning for reverse-chronological order
    save_json(MOD_LOGS_FILE, MOD_LOGS)
    
    # Update monthly metrics
    update_monthly_metric(f'total_{action.lower()}s')
    
    # Log member counts on every major action for historical reference
    SERVER_METRICS['monthly_summary']['member_count_at_action'] = len(guild_members)
    save_json(METRICS_FILE, SERVER_METRICS)


def update_monthly_metric(key):
    """Increments a counter in the SERVER_METRICS monthly_summary and saves."""
    global SERVER_METRICS
    
    today = datetime.now().date()
    last_reset_str = SERVER_METRICS['monthly_summary'].get('last_reset', str(today))
    last_reset_date = datetime.fromisoformat(last_reset_str).date()
    
    # Simple monthly reset logic: if the month has changed, reset the counters
    if today.month != last_reset_date.month:
        print("INFO: Monthly metric reset triggered.")
        SERVER_METRICS['monthly_summary'] = {
            'total_mutes': 0,
            'total_bans': 0,
            'total_kicks': 0,
            'last_reset': str(today)
        }

    if key in SERVER_METRICS['monthly_summary']:
        SERVER_METRICS['monthly_summary'][key] += 1
        save_json(METRICS_FILE, SERVER_METRICS)

@tasks.loop(minutes=1.0)
async def metric_saver_loop():
    """
    Background loop to periodically save in-memory metrics (chatters, activity) 
    to the disk to reduce frequent file I/O.
    """
    global SERVER_METRICS
    
    # Convert in-memory channel activity back to a standard dictionary for JSON
    SERVER_METRICS['channel_activity_log'] = {str(k): v for k, v in CHANNEL_ACTIVITY.items()}
    
    # Update Active Chatters List (clears monthly in a better loop, but for now we just track unique)
    # Note: For true monthly reset, this should be handled in an on_ready loop. 
    # For this iteration, we keep it simple by just saving the current state.
    
    save_json(METRICS_FILE, SERVER_METRICS)
    # print("INFO: Metrics saved to disk.")


# --- DISCORD EVENTS ---

@bot.event
async def on_ready():
    """Confirms the bot is connected and starts the metric saver loop."""
    print('---------------------------------')
    print(f'Logged in as: {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print(f'Discord.py Version: {discord.__version__}')
    print('---------------------------------')
    
    # Start background tasks
    if not metric_saver_loop.is_running():
        metric_saver_loop.start()
        print("INFO: Metric saver loop started.")


@bot.event
async def on_member_join(member):
    """
    Handles ban evasion check and logs the join event for metrics.
    """
    # --- BAN EVASION CHECK (Existing Logic) ---
    is_banned = any(log['target_id'] == str(member.id) and log['action'] == 'BAN' for log in MOD_LOGS['logs'])
    
    if is_banned:
        try:
            # Re-ban the user and notify staff
            await member.ban(reason="Auto-Eviction Enforcement: Detected prior BAN record in permanent log.")
            mod_channel = bot.get_channel(MOD_ALERT_CHANNEL_ID)
            if mod_channel:
                embed = discord.Embed(
                    title="🚫 AUTO-EVICTION ENFORCEMENT",
                    description=f"User **{member.display_name}** (`{member.id}`) attempted to rejoin but was **INSTANTLY RE-BANNED**.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Reason", value="Detected prior BAN in permanent record.")
                await mod_channel.send(embed=embed)
            print(f"ACTION: Auto-re-banned user {member.id} for evasion.")
            return

        except Exception as e:
            print(f"ERROR: Failed to auto-ban {member.id}. {e}")

    # --- METRIC LOGGING (NEW) ---
    today_str = datetime.now().strftime('%Y-%m-%d')
    SERVER_METRICS['join_log'][today_str] = SERVER_METRICS['join_log'].get(today_str, 0) + 1
    save_json(METRICS_FILE, SERVER_METRICS)
    print(f"INFO: Logged member join for {today_str}.")


@bot.event
async def on_member_remove(member):
    """
    Logs the leave event for metrics (Churn tracking).
    """
    # --- METRIC LOGGING (NEW) ---
    today_str = datetime.now().strftime('%Y-%m-%d')
    SERVER_METRICS['leave_log'][today_str] = SERVER_METRICS['leave_log'].get(today_str, 0) + 1
    save_json(METRICS_FILE, SERVER_METRICS)
    print(f"INFO: Logged member leave for {today_str}.")


@bot.event
async def on_raw_reaction_add(payload):
    """Handles the automatic role assignment for verification."""
    if payload.channel_id == VERIFICATION_CHANNEL_ID and str(payload.emoji) == VERIFICATION_EMOJI:
        guild = bot.get_guild(payload.guild_id)
        if not guild: return

        member = guild.get_member(payload.user_id)
        if not member or member.bot: return

        member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
        if member_role and member_role not in member.roles:
            try:
                await member.add_roles(member_role, reason="Verification through reaction.")
                print(f"ACTION: Granted {MEMBER_ROLE_NAME} to {member.display_name} via reaction.")
                
                # Optional: Send a welcoming DM or channel message here
                
            except Exception as e:
                print(f"ERROR: Could not grant role to {member.display_name}: {e}")


@bot.event
async def on_message(message):
    """Handles content filtering and metric tracking."""
    
    # Ignore bot messages and empty messages
    if message.author.bot or not message.content:
        return

    # --- METRIC TRACKING (NEW) ---
    # Update in-memory metrics on every message
    user_id = str(message.author.id)
    if user_id not in ACTIVE_CHATTERS:
        ACTIVE_CHATTERS.add(user_id)
        
    CHANNEL_ACTIVITY[message.channel.id] += 1

    # --- CONTENT FILTERING (Existing Logic) ---
    
    # 1. Spam Link Filter
    suspicious_links = ['bit.ly', 'tinyurl.com', '.xyz', '.cc', 'discord.gg']
    if any(link in message.content.lower() for link in suspicious_links) and not message.author.guild_permissions.manage_messages:
        try:
            await message.delete()
            
            # Send temporary removal notice
            notice_message = await message.channel.send(
                f"**Neighborhood Watch:** {message.author.mention}, that type of link is automatically filtered. Please contact staff if this was an error."
            )
            await asyncio.sleep(5)
            await notice_message.delete()
            print(f"ACTION: Deleted suspicious link from {message.author.display_name} in #{message.channel.name}")
            return
        except discord.errors.Forbidden:
            print("ERROR: Bot does not have permission to delete messages for spam filtering.")
            
    # 2. Keyword Filter (Example: 'promotional', 'shill', etc.)
    prohibited_keywords = ['promotional-phrase', 'shill-content-example']
    if any(keyword in message.content.lower() for keyword in prohibited_keywords) and not message.author.guild_permissions.manage_messages:
        # Same deletion logic as above
        try:
            await message.delete()
            notice_message = await message.channel.send(
                f"**Neighborhood Watch:** {message.author.mention}, certain keywords are prohibited. This is an automatic deletion."
            )
            await asyncio.sleep(5)
            await notice_message.delete()
            print(f"ACTION: Deleted message containing prohibited keyword from {message.author.display_name} in #{message.channel.name}")
            return
        except discord.errors.Forbidden:
            print("ERROR: Bot does not have permission to delete messages for keyword filtering.")
    
    # Process commands after all filters
    await bot.process_commands(message)


# --- STAFF AND MODERATION COMMANDS ---

def is_moderator(ctx):
    """Check if the user has permission to manage messages."""
    return ctx.author.guild_permissions.manage_messages

@bot.command(name='commands', help='[STAFF] Displays a dynamic list of commands you have permission to use.')
@commands.check(is_moderator)
async def list_commands(ctx):
    """
    New command: Dynamically lists all moderator commands in an embed.
    """
    command_list = []
    
    # Filter commands the user can run (which, due to the check, will be all below)
    for command in bot.commands:
        if command.hidden or not command.help:
            continue
        
        # Check if the command has the is_moderator check
        if any(check.__name__ == 'is_moderator' for check in command.checks):
            command_list.append(f"**{COMMAND_PREFIX}{command.name}** {command.signature or ''}\n> *{command.help}*")

    embed = discord.Embed(
        title="🛠️ GND Manager: Staff Command Panel",
        description="Here are the commands you have access to:",
        color=discord.Color.dark_teal()
    )
    
    embed.add_field(name="ADMIN COMMANDS", value="\n".join(command_list), inline=False)
    embed.set_footer(text=f"Prefix: {COMMAND_PREFIX} | Mod Channel ID: {MOD_ALERT_CHANNEL_ID}")
    
    await ctx.send(embed=embed)


@bot.command(name='say', help='[ADMIN] Posts a clean message to a specified channel via the bot. Usage: !say #channel Your message here')
@commands.check(is_moderator)
async def say_command(ctx, channel: discord.TextChannel, *, message):
    """Admin command to post a message to a specific channel."""
    try:
        await ctx.message.delete()
        await channel.send(message)
        
        # Send ephemeral confirmation back to the admin
        await ctx.author.send(f"✅ Successfully posted to **#{channel.name}**:\n>>> {message}", delete_after=5)
        
    except discord.errors.Forbidden:
        await ctx.author.send("❌ Error: I do not have permission to post to that channel.", delete_after=10)
    except Exception as e:
        await ctx.author.send(f"❌ An error occurred: {e}", delete_after=10)


@bot.command(name='purge', help='[STAFF] Deletes a specified number of messages. Usage: !purge 10')
@commands.check(is_moderator)
async def purge_command(ctx, count: int):
    """Deletes a specified number of recent messages in the channel."""
    if count < 1:
        await ctx.send("Please specify a number greater than 0.")
        return
        
    try:
        deleted = await ctx.channel.purge(limit=count + 1) # +1 to include the command message itself
        notice = await ctx.send(f"🧹 Clean-Up Duty: Deleted **{len(deleted) - 1}** messages.", delete_after=5)
    except discord.errors.Forbidden:
        await ctx.send("❌ Error: I do not have permission to delete messages in this channel.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred during purge: {e}")


@bot.command(name='kick', help='[STAFF] Kicks a member. Usage: !kick @Member reason')
@commands.check(is_moderator)
async def kick_command(ctx, member: discord.Member, *, reason="No reason provided"):
    """Kicks a member and logs the action."""
    try:
        await member.kick(reason=reason)
        update_log_and_metrics('KICK', member.id, ctx.author.id, reason, ctx.guild.members) # Log and update metrics (NEW)
        
        embed = discord.Embed(
            title="👢 EVICTION NOTICE: KICK", 
            description=f"User {member.mention} was kicked.", 
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Action by: {ctx.author.name} | ID: {member.id}")
        
        # Send log to mod channel and success message in current channel
        mod_channel = bot.get_channel(MOD_ALERT_CHANNEL_ID)
        if mod_channel: await mod_channel.send(embed=embed)
        await ctx.send(f"✅ Kicked {member.mention}.", delete_after=5)
        
    except discord.errors.Forbidden:
        await ctx.send("❌ Error: I do not have permission to kick this user.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")


@bot.command(name='ban', help='[ADMIN] Bans a member permanently. Usage: !ban @Member reason')
@commands.check(is_moderator)
async def ban_command(ctx, member: discord.Member, *, reason="No reason provided"):
    """Bans a member and logs the action for permanent record."""
    try:
        await member.ban(reason=reason)
        update_log_and_metrics('BAN', member.id, ctx.author.id, reason, ctx.guild.members) # Log and update metrics (NEW)

        embed = discord.Embed(
            title="⛔ EVICTION NOTICE: BAN", 
            description=f"User {member.mention} was permanently banned.", 
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Action by: {ctx.author.name} | ID: {member.id}")

        mod_channel = bot.get_channel(MOD_ALERT_CHANNEL_ID)
        if mod_channel: await mod_channel.send(embed=embed)
        await ctx.send(f"✅ Banned {member.mention}. Auto-Eviction Enforcement is now active for this ID.", delete_after=5)

    except discord.errors.Forbidden:
        await ctx.send("❌ Error: I do not have permission to ban this user.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")


@bot.command(name='mute', help='[STAFF] Mutes a member temporarily. Usage: !mute @Member reason')
@commands.check(is_moderator)
async def mute_command(ctx, member: discord.Member, *, reason="No reason provided"):
    """Mutes a member by applying the Muted role and logs the action."""
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    
    if not muted_role:
        await ctx.send(f"❌ Error: The required role '{MUTED_ROLE_NAME}' does not exist.", delete_after=10)
        return
        
    try:
        await member.add_roles(muted_role, reason=reason)
        update_log_and_metrics('MUTE', member.id, ctx.author.id, reason, ctx.guild.members) # Log and update metrics (NEW)
        
        embed = discord.Embed(
            title="🔇 TEMPORARY SUSPENSION: MUTE", 
            description=f"User {member.mention} has been muted.", 
            color=discord.Color.dark_grey()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Action by: {ctx.author.name}")

        mod_channel = bot.get_channel(MOD_ALERT_CHANNEL_ID)
        if mod_channel: await mod_channel.send(embed=embed)
        await ctx.send(f"✅ Muted {member.mention}.", delete_after=5)

    except discord.errors.Forbidden:
        await ctx.send("❌ Error: I do not have permission to modify this user's roles.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")


@bot.command(name='unmute', help='[STAFF] Unmutes a member. Usage: !unmute @Member')
@commands.check(is_moderator)
async def unmute_command(ctx, member: discord.Member):
    """Unmutes a member by removing the Muted role."""
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    
    if not muted_role:
        await ctx.send(f"❌ Error: The required role '{MUTED_ROLE_NAME}' does not exist.", delete_after=10)
        return
        
    try:
        await member.remove_roles(muted_role, reason="Unmuted by moderator.")
        await ctx.send(f"✅ Unmuted {member.mention}.", delete_after=5)
        
    except discord.errors.Forbidden:
        await ctx.send("❌ Error: I do not have permission to modify this user's roles.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")


@bot.command(name='report', help='[ALL] Discreetly report a member or issue. Usage: !report @Member reason')
async def report_command(ctx, member: discord.Member, *, reason="No reason provided"):
    """Allows any member to report a violation directly to the mod channel and logs the action."""
    try:
        # 1. Log the report (NEW: Now uses the logging function)
        update_log_and_metrics('REPORT', member.id, ctx.author.id, reason, ctx.guild.members)
        
        # 2. Send alert to mod channel
        mod_channel = bot.get_channel(MOD_ALERT_CHANNEL_ID)
        if mod_channel:
            embed = discord.Embed(
                title="🚨 TATTLETALE TOOL: NEW REPORT",
                description=f"**Reported User:** {member.mention} (`{member.id}`)\n**Reported By:** {ctx.author.mention} (`{ctx.author.id}`)\n**Channel:** {ctx.channel.mention}",
                color=discord.Color.light_grey()
            )
            embed.add_field(name="Reason/Details", value=reason, inline=False)
            await mod_channel.send(embed=embed)

        # 3. Confirmation to the reporter
        await ctx.message.delete()
        await ctx.author.send("✅ Your report has been submitted to the moderator team discreetly. Thank you.", delete_after=10)
        
    except Exception as e:
        await ctx.author.send(f"❌ An error occurred while submitting your report: {e}", delete_after=10)


@bot.command(name='whois', help='[STAFF] Looks up a user\'s ID and displays their recent disciplinary history. Usage: !whois @Member')
@commands.check(is_moderator)
async def whois_command(ctx, member: discord.Member):
    """Provides a security profile for a user based on their permanent log."""
    
    target_id = str(member.id)
    
    # Filter log entries for the target user ID
    user_logs = [log for log in MOD_LOGS['logs'] if log['target_id'] == target_id]
    
    embed = discord.Embed(
        title=f"👤 Background Check: {member.display_name}",
        description=f"Account Details and Disciplinary History.",
        color=discord.Color.blue()
    )
    
    # Details Field
    embed.add_field(name="Account Info", value=(
        f"**ID:** `{target_id}`\n"
        f"**Joined:** {member.joined_at.strftime('%Y-%m-%d %H:%M')}\n"
        f"**Created:** {member.created_at.strftime('%Y-%m-%d %H:%M')}"
    ), inline=False)
    
    # History Field
    if user_logs:
        history_summary = ""
        # Show only the last 5 relevant logs
        for log in user_logs[:5]:
            # Format timestamp to be readable
            dt_obj = datetime.fromisoformat(log['timestamp'])
            time_str = dt_obj.strftime('%m/%d %H:%M')
            
            history_summary += f"**[{log['action']}** on {time_str}] Reason: {log['reason']}\n"
            
        embed.add_field(name=f"Permanent Record History ({len(user_logs)} Total)", value=history_summary, inline=False)
    else:
        embed.add_field(name="Permanent Record History", value="Clean slate! No logs found.", inline=False)
        
    await ctx.send(embed=embed)


@bot.command(name='verify', help='[ALL] Manually grants the Member role if needed.')
async def verify_command(ctx):
    """Allows users to manually trigger verification."""
    member_role = discord.utils.get(ctx.guild.roles, name=MEMBER_ROLE_NAME)
    
    if not member_role:
        await ctx.send(f"❌ Error: The required role '{MEMBER_ROLE_NAME}' does not exist.", delete_after=10)
        return
        
    if member_role in ctx.author.roles:
        await ctx.send("✅ You are already verified and have the Member role.", delete_after=5)
    else:
        try:
            await ctx.author.add_roles(member_role, reason="Manual verification command.")
            await ctx.send("✅ Welcome to the neighborhood! You have been verified.", delete_after=5)
        except Exception as e:
            await ctx.send(f"❌ Error adding role: {e}", delete_after=10)

# --- BOT RUNNER FUNCTION ---

def run_bot():
    """Starts the bot using the retrieved token."""
    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable is not set.")
    else:
        try:
            # We use bot.run in app.py's separate thread, so this function is technically unused 
            # in the production deployment but kept for local testing structure.
            # bot.run(TOKEN)
            pass
        except discord.errors.LoginFailure:
            print("ERROR: Bot failed to log in. Check your DISCORD_BOT_TOKEN.")
        except Exception as e:
            print(f"An unexpected error occurred during bot run: {e}")
    run_bot()
