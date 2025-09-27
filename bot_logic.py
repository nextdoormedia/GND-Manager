# bot_logic.py
# Core logic, commands, and events for Housemate Ryker.

import os
import json
from datetime import datetime
from discord.ext import commands
import discord
import asyncio

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

# Intents are mandatory for modern discord bots to declare what events they listen to.
intents = discord.Intents.default()
intents.message_content = True
intents.members = True # <-- CLEANED: This line caused the SyntaxError
intents.presences = True
intents.reactions = True

# Initialize the bot client
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
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Housemate Ryker is online and monitoring the neighborhood.')

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
            print("Error: Bot does not have permission to ban the user for evasion.")

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
            print("Error: Bot lacks permissions to assign the Member role.")


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
            print("Error: Bot lacks permissions to delete messages.")
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
    """Ryker's Bulletin: Securely posts a clean message to a specified channel."""
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
