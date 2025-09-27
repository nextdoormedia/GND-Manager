# bot_logic.py
# Core logic, commands, and events for GND Manager.

import os
import json
from datetime import datetime, timedelta
from discord.ext import commands
import discord
import asyncio
import time # Added for !status command

# --- CONFIGURATION & SETUP ---

# Fetches the bot token from the environment variable set on Render
TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
MOD_LOGS_FILE = 'mod_logs.json'
COMMAND_PREFIX = '!'
MEMBER_ROLE_NAME = 'Member'
MUTED_ROLE_NAME = 'Muted'
MOD_ALERT_CHANNEL_ID = 123456789012345678  # Placeholder: Replace with actual Mod channel ID
VERIFICATION_CHANNEL_ID = 123456789012345679 # Placeholder: Replace with actual Welcome channel ID
VERIFICATION_EMOJI = '✅'

# Global variable to track bot start time for !status
BOT_START_TIME = time.time()

# Intents are mandatory for modern discord bots to declare what events they listen to.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.reactions = True

# Initialize the bot client (GND Manager)
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# --- MODERATION LOGIC (mod_logs.json) ---

def load_mod_logs():
    """Loads the disciplinary log file, initializing if necessary."""
    if not os.path.exists(MOD_LOGS_FILE):
        return []
    try:
        with open(MOD_LOGS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print("Warning: Could not load mod_logs.json. Starting with an empty log.")
        return []

def save_mod_logs(logs):
    """Saves the current state of the disciplinary logs."""
    try:
        with open(MOD_LOGS_FILE, 'w') as f:
            json.dump(logs, f, indent=4)
    except IOError as e:
        print(f"Error saving mod_logs.json: {e}")

def log_action(user_id, moderator_id, action, reason):
    """Adds a new disciplinary action to the log."""
    logs = load_mod_logs()
    new_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': str(user_id),
        'moderator_id': str(moderator_id),
        'action': action.upper(),
        'reason': reason
    }
    logs.append(new_entry)
    save_mod_logs(logs)
    return new_entry

# --- BOT EVENTS ---

@bot.event
async def on_ready():
    """Confirms the bot is connected and operational."""
    global BOT_START_TIME
    BOT_START_TIME = time.time() # Ensure the start time is set/reset on connection
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('GND Manager is online and monitoring the neighborhood.')

@bot.event
async def on_member_join(member):
    """Handles auto-eviction and initial verification reminders."""
    # 1. Ban Evasion Check
    logs = load_mod_logs()
    ban_history = [log for log in logs if log['user_id'] == str(member.id) and log['action'] == 'BAN']

    if ban_history:
        print(f"Ban Evasion Alert: User {member.name} ({member.id}) tried to join but was previously banned. Re-banning.")
        try:
            await member.ban(reason="Attempted Ban Evasion (Permanent Record Match)")
            # Log the re-ban action
            log_action(member.id, bot.user.id, 'AUTO_REBAN', 'Attempted Ban Evasion')
        except discord.Forbidden:
            print("Error: GND Manager does not have permission to ban the user for evasion.")

    # 2. Verification Reminder (If not already banned)
    else:
        # Send a private welcome message or a message to the verification channel
        welcome_channel = bot.get_channel(VERIFICATION_CHANNEL_ID)
        if welcome_channel:
            # We assume the rules message is in this channel, which they must react to.
            await welcome_channel.send(
                f"Welcome, {member.mention}! To unlock the server, please read the rules and react with the {VERIFICATION_EMOJI} emoji in this channel.",
                delete_after=600 # Delete reminder after 10 minutes
            )

@bot.event
async def on_raw_reaction_add(payload):
    """Handles the automatic verification via reaction."""
    if payload.channel_id != VERIFICATION_CHANNEL_ID or str(payload.emoji) != VERIFICATION_EMOJI:
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    member = guild.get_member(payload.user_id)
    if member.bot:
        return

    member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
    if member_role and member_role not in member.roles:
        try:
            await member.add_roles(member_role)
            print(f"Verification successful: {member.name} received the {MEMBER_ROLE_NAME} role.")
            # Optional: Send a brief confirmation message in the channel and delete it quickly
            channel = bot.get_channel(payload.channel_id)
            if channel:
                 await channel.send(f"Welcome aboard, {member.mention}! You've been verified and unlocked the rest of the neighborhood.", delete_after=10)
        except discord.Forbidden:
            print("Error: GND Manager lacks permissions to assign the Member role.")


@bot.event
async def on_message(message):
    """Content filtering and command handling."""
    if message.author.bot:
        return

    # 1. Content Filters (Example: simple link filter)
    suspicious_links = ['http://', 'https://', 'bit.ly', '.com']
    if any(link in message.content for link in suspicious_links):
        try:
            await message.delete()
            # Send a temporary removal notice
            warning_msg = await message.channel.send(f"{message.author.mention}, that link has been removed by the Neighborhood Watch filter. Please use designated channels for promotion.", delete_after=8)
        except discord.Forbidden:
            print("Error: GND Manager lacks permissions to delete messages.")
        return # Stop processing to prevent command check

    # 2. Process commands
    await bot.process_commands(message)

# --- MODERATION COMMANDS (Admin-Only) ---

def is_admin():
    """Simple check function to limit commands to users with 'administrator' permission."""
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        await ctx.send("🚨 **ACCESS DENIED:** You need Admin privileges to use this tool.", delete_after=10)
        return False
    return commands.check(predicate)

@bot.command(name='say')
@is_admin()
async def say_command(ctx, channel: discord.TextChannel, *, message):
    """Manager's Bulletin: Securely posts a clean message to a specified channel."""
    await ctx.message.delete()
    await channel.send(message)
    print(f"Admin message sent to #{channel.name} by {ctx.author.name}")

@bot.command(name='purge')
@is_admin()
async def purge_command(ctx, count: int):
    """Clean-Up Duty: Deletes a specified number of messages."""
    await ctx.message.delete() # Delete the command itself
    deleted = await ctx.channel.purge(limit=count)
    
    # Post temporary success notice
    success_msg = await ctx.channel.send(
        f'🧹 Clean-Up Duty: Deleted **{len(deleted)}** messages.',
        delete_after=5
    )
    print(f"Purge successful in #{ctx.channel.name}: {len(deleted)} messages deleted by {ctx.author.name}")

@bot.command(name='kick')
@is_admin()
async def kick_command(ctx, member: discord.Member, *, reason='No reason provided'):
    """Eviction Notice: Kicks a member from the server."""
    await ctx.message.delete()
    
    try:
        await member.kick(reason=reason)
        # Log the action
        log_action(member.id, ctx.author.id, 'KICK', reason)

        await ctx.send(f'🚪 **Eviction Notice issued to {member.mention}:** Kicked for "{reason}".', delete_after=15)
        print(f"Kicked {member.name} ({member.id}). Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("Error: I do not have permissions to kick that user.", delete_after=10)

@bot.command(name='ban')
@is_admin()
async def ban_command(ctx, user: discord.User, *, reason='No reason provided'):
    """Eviction Notice: Bans a user from the server."""
    await ctx.message.delete()

    try:
        await ctx.guild.ban(user, reason=reason)
        # Log the action
        log_action(user.id, ctx.author.id, 'BAN', reason)
        
        await ctx.send(f'🔨 **Eviction Notice served to {user.name}:** Permanently Banned for "{reason}".', delete_after=15)
        print(f"Banned {user.name} ({user.id}). Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("Error: I do not have permissions to ban that user.", delete_after=10)
    except discord.NotFound:
        await ctx.send("Error: User not found.", delete_after=10)


@bot.command(name='mute')
@is_admin()
async def mute_command(ctx, member: discord.Member, *, reason='No reason provided'):
    """Temporary Suspension: Mutes a member."""
    await ctx.message.delete()
    
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if not muted_role:
        await ctx.send(f"Error: Muted role ('{MUTED_ROLE_NAME}') not found. Please create it first.", delete_after=10)
        return

    try:
        await member.add_roles(muted_role, reason=reason)
        log_action(member.id, ctx.author.id, 'MUTE', reason)
        
        await ctx.send(f'🔇 **Temporary Suspension for {member.mention}:** Muted for "{reason}".', delete_after=15)
    except discord.Forbidden:
        await ctx.send("Error: I do not have permissions to assign the Muted role.", delete_after=10)


@bot.command(name='unmute')
@is_admin()
async def unmute_command(ctx, member: discord.Member, *, reason='Mute lifted'):
    """Lifts a temporary suspension (unmutes a member)."""
    await ctx.message.delete()
    
    muted_role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if not muted_role:
        await ctx.send(f"Error: Muted role ('{MUTED_ROLE_NAME}') not found.", delete_after=10)
        return

    try:
        await member.remove_roles(muted_role, reason=reason)
        log_action(member.id, ctx.author.id, 'UNMUTE', reason)
        
        await ctx.send(f'🔊 **Suspension Lifted for {member.mention}.**', delete_after=15)
    except discord.Forbidden:
        await ctx.send("Error: I do not have permissions to remove the Muted role.", delete_after=10)


@bot.command(name='whois')
@is_admin()
async def whois_command(ctx, member: discord.Member):
    """Background Check: Retrieves user details and moderation history."""
    await ctx.message.delete()

    logs = load_mod_logs()
    user_logs = [log for log in logs if log['user_id'] == str(member.id)]
    
    embed = discord.Embed(
        title=f"🔎 Background Check: {member.display_name}",
        description=f"User ID: `{member.id}`",
        color=discord.Color.dark_blue()
    )
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Total Logs", value=len(user_logs), inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    
    # Display last 3 disciplinary actions
    history_text = ""
    if user_logs:
        # Sort by timestamp (newest first) and take the last 3
        recent_logs = sorted(user_logs, key=lambda x: x['timestamp'], reverse=True)[:3]
        
        for log in recent_logs:
            timestamp = datetime.fromisoformat(log['timestamp']).strftime('%Y-%m-%d %H:%M')
            history_text += (
                f"**{log['action']}** by Mod `{log['moderator_id']}`\n"
                f"> Reason: *{log['reason']}* (_{timestamp}_)\n"
            )
    else:
        history_text = "No prior disciplinary history found. (Clean Record)"

    embed.add_field(name="Recent Permanent Record (Last 3)", value=history_text or "N/A", inline=False)
    
    await ctx.send(embed=embed)


@bot.command(name='report')
async def report_command(ctx, member: discord.Member, *, reason):
    """Tattletale Tool: Discreetly reports a user to moderators."""
    await ctx.message.delete()
    
    mod_channel = bot.get_channel(MOD_ALERT_CHANNEL_ID)
    if mod_channel:
        # 1. Log the action (Reporter ID, Reported User ID, Action, Reason)
        log_entry = log_action(member.id, ctx.author.id, 'REPORT', reason)

        # 2. Notify the mod channel
        embed = discord.Embed(
            title="⚠️ Tattletale Tool: New Report Filed",
            description=f"**Reported User:** {member.mention} (`{member.id}`)\n**Reported By:** {ctx.author.mention} (`{ctx.author.id}`)",
            color=discord.Color.red(),
            timestamp=datetime.fromisoformat(log_entry['timestamp'])
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Log ID: {len(load_mod_logs())}")
        
        await mod_channel.send(embed=embed)
        
        # 3. Confirmation to the reporter
        try:
            await ctx.author.send("✅ **Report Received!** Thank you for using the Tattletale Tool. Staff have been notified and will review your report shortly.")
        except discord.Forbidden:
            pass # Cannot send DM, but the mod alert was sent

    else:
        # Fallback if mod channel isn't configured correctly
        await ctx.author.send("🚨 Error: The moderator alert channel is not configured correctly. Please notify an Admin manually.")

# --- USER COMMANDS (Manager Utilities) ---

@bot.command(name='status')
async def status_command(ctx):
    """The Premises Report: Displays the Manager's health (uptime and latency)."""
    # Calculate uptime
    current_time = time.time()
    difference = int(round(current_time - BOT_START_TIME))
    uptime = str(timedelta(seconds=difference))

    # Calculate latency (ping)
    latency = round(bot.latency * 1000, 2) # Latency in milliseconds
    
    embed = discord.Embed(
        title="📈 GND Manager: Premises Report",
        description="The system is running smoothly and monitoring operations.",
        color=discord.Color.green()
    )
    embed.add_field(name="🛰️ Latency (Ping)", value=f"{latency} ms", inline=True)
    embed.add_field(name="⏱️ Uptime", value=uptime, inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)


@bot.command(name='rules')
async def rules_command(ctx):
    """The Lease Agreement: Provides a quick summary of essential server rules."""
    
    rules_content = """
    | Rule | Summary | Consequence |
    | :--- | :--- | :--- |
    | **18+ ONLY** | You must be 18 years of age or older to be in the community. | Permanent Ban |
    | **Respect** | Treat all members with courtesy; no harassment or hate speech. | Moderation Action |
    | **No Unsolicited DMs** | Do not send unwanted private messages to other members. | Moderation Action |
    | **Content** | All content must adhere to Discord ToS and legal standards. | Immediate Ban |
    | **Promotion** | Self-Promotion is **only** allowed in the designated channel. | Warning/Deletion |
    | **Moderators** | Follow all instructions from the moderation team. | Moderation Action |
    """

    embed = discord.Embed(
        title="📜 The Lease Agreement (Quick Rules)",
        description="The essential rules for maintaining a safe and respectful neighborhood.",
        color=discord.Color.light_grey()
    )
    # The markdown table is added directly to a field
    embed.add_field(name="Core Conduct Guidelines", value=rules_content, inline=False)
    embed.set_footer(text="If you need to report a violation, use !report @user [reason].")
    
    await ctx.send(embed=embed)


@bot.command(name='invite')
async def invite_command(ctx):
    """The Key: Generates a permanent invite link to share the community."""
    
    # Using the static invite link provided by the user
    INVITE_LINK = "https://discord.gg/EKekh3wHYQ" 
    
    embed = discord.Embed(
        title="🔑 Share the Key",
        description="Invite your friends to the Neighborhood!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Permanent Invitation Link", value=f"[Click here to join the community!]({INVITE_LINK})", inline=False)
    embed.set_footer(text="Thanks for helping us grow the neighborhood!")
    
    await ctx.send(embed=embed)


@bot.command(name='serverstats')
async def serverstats_command(ctx):
    """The Ledger: Displays robust activity and administrative data points."""
    
    # --- NOTE: This is MOCK DATA, ready to be replaced with real database queries ---
    # Future development involves calculating these metrics from a database (e.g., Firestore).
    
    # Fetch guild member counts
    member_count = ctx.guild.member_count
    
    # Mock Statistics
    total_messages_24h = "3,450" # Placeholder
    avg_daily_messages = "4,120" # Placeholder
    most_active_channel = "#main-chat (38% activity)" # Placeholder
    new_members_last_week = "74" # Placeholder
    total_mod_actions = len(load_mod_logs()) # Uses existing log data

    embed = discord.Embed(
        title="📊 The Ledger: Neighborhood Statistics",
        description=f"Comprehensive data monitored by GND Manager on the server's health and activity.",
        color=discord.Color.dark_purple()
    )
    
    embed.add_field(name="🏘️ Current Population", value=f"{member_count} Members", inline=True)
    embed.add_field(name="💬 Messages (Last 24h)", value=total_messages_24h, inline=True)
    embed.add_field(name="📈 Average Daily Chat", value=avg_daily_messages, inline=True)

    embed.add_field(name="🔥 Most Active Channel", value=most_active_channel, inline=True)
    embed.add_field(name="🆕 New Members (Last 7d)", value=new_members_last_week, inline=True)
    embed.add_field(name="🚨 Total Mod Actions", value=total_mod_actions, inline=True)

    embed.set_footer(text="GND Manager is currently tracking these metrics for expansion.")
    
    await ctx.send(embed=embed)


@bot.command(name='schedule')
async def schedule_command(ctx):
    """Official Weekly Schedule: Displays all content drops and community events."""

    embed = discord.Embed(
        title="📅 Official Weekly Schedule & Events",
        description="Here is the complete schedule for all content, streams, and community events.",
        color=discord.Color.red()
    )

    embed.add_field(
        name="💻 Content & Streams",
        value=(
            "**Saturday (7-10 PM Central):** 🛋️ Cam Stream on Chaturbate\n"
            "**Sunday (Weekly Drop):** 🎥 New Video Drop on PornHub\n"
            "**Mondays (Anytime):** 💎 Discord Exclusive Drop in #content-drops"
        ),
        inline=False
    )

    embed.add_field(
        name="🏘️ Community Events (Discord Exclusive)",
        value=(
            "**Tuesday:** 🗳️ Weekly Poll in #polls\n"
            "**Wednesday:** 🏠 House Meeting (Q&A/Hangout) in Stage Channel (Time announced in #stream-alerts)"
        ),
        inline=False
    )
    
    embed.set_footer(text="⚡ Bonus Streams are announced by 6 PM Central in #stream-alerts.")
    
    await ctx.send(embed=embed)


@bot.command(name='links')
async def links_command(ctx):
    """Links: Provides all essential content platform links."""

    embed = discord.Embed(
        title="🔗 Manager's Links & Platform Support",
        description="Access all our platforms and support links here.",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Main Website", value="[guysnextdoor.netlify.app](https://guysnextdoor.netlify.app)", inline=False)
    embed.add_field(name="Chaturbate", value="[chaturbate.com/hotcockjock99](https://chaturbate.com/hotcockjock99)", inline=False)
    embed.add_field(name="PornHub", value="[pornhub.com/model/guysnextdoor](https://pornhub.com/model/guysnextdoor)", inline=False)
    embed.add_field(name="Discord Invite", value="[discord.gg/EKekh3wHYQ](https://discord.gg/EKekh3wHYQ)", inline=False)
    embed.add_field(name="Tip Jar", value="**COMING SOON**", inline=False)
    
    embed.set_footer(text="Thank you for your support!")
    
    await ctx.send(embed=embed)

# --- BOT RUNNER FUNCTION ---

def run_bot():
    """Starts the bot using the retrieved token."""
    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable is not set.")
    else:
        try:
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("ERROR: Bot failed to log in. Check your DISCORD_BOT_TOKEN.")
        except Exception as e:
            print(f"An unexpected error occurred during bot execution: {e}")

if __name__ == '__main__':
    # This block is not used in the Render deployment strategy (app.py handles the run), 
    # but is useful for local testing.
    run_bot()
