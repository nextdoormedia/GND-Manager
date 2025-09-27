import discord
from discord.ext import commands
from datetime import datetime
import os, random, asyncio

# --- CONFIGURATION CONSTANTS (Control Panel) ---

# CRITICAL IDs: REPLACE THESE WITH YOUR SERVER'S ACTUAL IDs (if different from existing)
WELCOME_CHANNEL_ID = 1420121916404007136    # The channel where the rules/verification message is.
VERIFICATION_MESSAGE_ID = 1420121916404007137 # The specific rules message users react to.
VERIFICATION_EMOJI = "✅"                 # The specific emoji users react with.
MEMBER_ROLE_NAME = "Member"              # The role to grant upon verification.
MOD_ALERTS_CHANNEL_ID = 1420127688248660081 

SELF_PROMO_CHANNEL_NAME = "self-promo"
# Content Filtering (for general channels)
FILTERED_KEYWORDS = ["illegal content", "graphic violence", "shock video", "dtxduo impersonation", "official admin", "mod giveaway"]
SPAM_LINKS = ["bit.ly", "tinyurl", "ow.ly", "shorte.st"]
PROMOTION_KEYWORDS = ["subscribe", "patreon", "youtube", "twitch", "onlyfans", "my channel", "check out my"]

# --- INTENTS SETUP (CRITICAL!) ---
intents = discord.Intents.default()
# Required for verification and on_member_join events
intents.members = True          
# CRITICAL for filtering and prefix commands (like !say)
intents.message_content = True  

# --- BOT INITIALIZATION ---
bot = commands.Bot(command_prefix='!', intents=intents)


# --- HELPER FUNCTIONS ---

async def send_mod_alert_embed(guild, title, description, color=discord.Color.yellow()):
    """Helper function to send a custom embed to the Mod Alerts Channel."""
    mod_channel = guild.get_channel(MOD_ALERTS_CHANNEL_ID)
    if not mod_channel:
        print(f"WARNING: Mod Alerts Channel (ID: {MOD_ALERTS_CHANNEL_ID}) not found.")
        return

    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=f"Alert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        await mod_channel.send(embed=embed)
    except Exception as e:
        print(f"Error sending mod alert: {e}")


# --- BOT EVENTS ---

@bot.event
async def on_ready():
    """Confirms the bot is logged in and ready."""
    print(f'✅ Housemate Ryker (Vibe-Free) is logged in as {bot.user}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="the Neighborhood Security"))

@bot.event
async def on_member_join(member):
    """Sends a welcome message and mod alert for new members."""
    welcome_channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        await welcome_channel.send(f"Welcome to the Neighborhood, {member.mention}! Please read the rules and verify to access the rest of the server.")
        
    await send_mod_alert_embed(
        member.guild, 
        "🚪 NEW NEIGHBOR ARRIVED", 
        f"{member.mention} ({member.id}) has joined the server.", 
        discord.Color.blue()
    )

@bot.event
async def on_member_remove(member):
    """Alerts mods when a member leaves."""
    await send_mod_alert_embed(
        member.guild,
        "🚪 NEIGHBOR REMOVED/LEFT",
        f"**{member.display_name}** ({member.id}) has left the server.",
        discord.Color.red()
    )


# --- VERIFICATION SYSTEM (REACTION) ---

@bot.event
async def on_raw_reaction_add(payload):
    """Handles reaction-based verification for new members."""
    # Check if the reaction is on the correct message in the correct channel
    if payload.message_id != VERIFICATION_MESSAGE_ID:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    # Check for the correct emoji
    if str(payload.emoji) == VERIFICATION_EMOJI:
        member_role = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
        if member_role and member_role not in member.roles:
            try:
                await member.add_roles(member_role)
                print(f"✅ VERIFY: {member.display_name} verified via reaction.")

                # Mod Alert
                await send_mod_alert_embed(
                    guild, 
                    "✅ MEMBER VERIFIED (Reaction)", 
                    f"{member.mention} ({member.display_name}) was granted the **{MEMBER_ROLE_NAME}** role.",
                    discord.Color.green()
                )

            except Exception as e:
                print(f"ERROR: Could not grant role to {member.display_name}: {e}")


# --- MESSAGE FILTERING AND MODERATION ---

@bot.event
async def on_message(message):
    """Runs all message-based checks (filters, promotion control)."""
    if message.author.bot:
        return

    # 1. Spam Link Filter
    for link in SPAM_LINKS:
        if link in message.content:
            await message.delete()
            await message.channel.send(f"⚠️ {message.author.mention}, please do not post abbreviated spam links. Message deleted.", delete_after=5)
            await send_mod_alert_embed(
                message.guild, 
                "🛑 SPAM LINK DELETED", 
                f"**User:** {message.author.display_name}\n**Channel:** {message.channel.mention}\n**Reason:** Contained suspected spam link.",
                discord.Color.dark_red()
            )
            # Stop processing, message is deleted
            return

    # 2. Forbidden Keyword Filter (Skips NSFW channels to avoid false positives)
    if not message.channel.is_nsfw():
        for keyword in FILTERED_KEYWORDS:
            if keyword in message.content.lower():
                await message.delete()
                await message.channel.send(f"🛑 {message.author.mention}, that content is prohibited in this neighborhood. Message deleted.", delete_after=5)
                await send_mod_alert_embed(
                    message.guild, 
                    "🛑 FORBIDDEN KEYWORD DELETED", 
                    f"**User:** {message.author.display_name}\n**Channel:** {message.channel.mention}\n**Keyword:** `{keyword}`",
                    discord.Color.dark_red()
                )
                # Stop processing, message is deleted
                return

    # 3. Self-Promotion Control
    if message.channel.name != SELF_PROMO_CHANNEL_NAME:
        for promo_word in PROMOTION_KEYWORDS:
            if promo_word in message.content.lower():
                await message.channel.send(f"📣 {message.author.mention}, please use the **#{SELF_PROMO_CHANNEL_NAME}** channel for self-promotion. Message stays, but please use the correct channel next time!", delete_after=10)
                await send_mod_alert_embed(
                    message.guild, 
                    "⚠️ PROMO WARNING ISSUED", 
                    f"**User:** {message.author.display_name} warned for posting promotional content in the wrong channel.",
                    discord.Color.yellow()
                )
                break # Only warn once per message

    # Process all remaining commands
    await bot.process_commands(message)


# --- CORE COMMANDS (UTILITY & ADMIN) ---

@bot.command()
async def verify(ctx):
    """Allows users to verify using a command if the reaction fails."""
    member_role = discord.utils.get(ctx.guild.roles, name=MEMBER_ROLE_NAME)
    member = ctx.author
    
    if not member_role:
        await ctx.send("❌ Error: The Member role is not set up correctly. Please contact an admin.")
        return

    if member_role in member.roles:
        await ctx.send("✅ You are already a verified Neighbor!", delete_after=5)
        await ctx.message.delete()
        return

    try:
        await member.add_roles(member_role)
        await ctx.send(f"✅ Welcome to the neighborhood, {member.mention}! You are now verified.", delete_after=5)
        await ctx.message.delete()
        print(f"✅ VERIFY: {member.display_name} verified via command.")
        
        # Mod Alert
        await send_mod_alert_embed(
            ctx.guild, 
            "✅ MEMBER VERIFIED (Command)", 
            f"{member.mention} ({member.display_name}) has self-verified using the **`!verify`** command.",
            discord.Color.green()
        )

    except Exception as e:
        await ctx.send("❌ Error: I couldn't grant you the role. Please check my permissions or contact an admin.", delete_after=5)
        print(f"ERROR: Could not grant role to {member.display_name} via !verify: {e}")

@bot.command()
async def report(ctx, member: discord.Member, *, reason: str):
    """Allows a user to privately report another member to the moderators."""
    mod_channel = ctx.guild.get_channel(MOD_ALERTS_CHANNEL_ID)
    if mod_channel:
        embed = discord.Embed(title="⚠️ USER REPORT", description="A member has submitted a private report.", color=discord.Color.red())
        embed.add_field(name="Reported User", value=member.mention, inline=True)
        embed.add_field(name="Reported By", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"Report time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await mod_channel.send(embed=embed)
        await ctx.message.delete()
        
        # Confirmation to the reporting user
        try:
             await ctx.author.send(f"✅ Your report against {member.display_name} has been securely sent to the moderation team. Thank you for helping keep the neighborhood safe.")
        except:
             # Fallback if DMs are closed
             await ctx.send(f"✅ Report submitted (could not send DM confirmation).", delete_after=5)

    else:
        await ctx.send("❌ Error: Could not find the Mod Alerts channel. Please contact an administrator directly.")

@bot.command()
@commands.has_permissions(administrator=True)
async def say(ctx, channel: discord.TextChannel, *, message: str):
    """Admin command to make the bot send a message to a specific channel."""
    try: 
        await channel.send(message) 
        await ctx.message.delete()
    except Exception as e: 
        await ctx.send(f"❌ Could not post message to {channel.mention}. Error: {e}")
        
@bot.command()
async def helpme(ctx):
    """Provides a simple list of the core remaining commands."""
    embed = discord.Embed(
        title="Housemate Ryker: Core Commands",
        description="Ryker is now focused purely on security and core utilities. All Vibe/XP/Shop commands have been retired.",
        color=discord.Color.blue()
    )
    embed.add_field(name="!verify", value="Grants the Member role if you can't use the reaction to verify.", inline=False)
    embed.add_field(name="!report @user [reason]", value="Privately sends an alert to the moderation team about a user or issue.", inline=False)
    embed.add_field(name="!helpme", value="Shows this message.", inline=False)
    embed.set_footer(text="The Invisible House Manager is here to keep the neighborhood safe and smooth.")
    await ctx.send(embed=embed)


# --- GLOBAL COMMAND ERROR HANDLER ---
@bot.event
async def on_command_error(ctx, error):
    # This prevents handling errors at the command level if they are ignored
    if hasattr(ctx.command, 'on_error'):
        return

    # Ignore command not found errors (keeps bot logs cleaner from typos, especially old Vibe commands)
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
         
    # Handle other errors
    print(f"Unhandled command error in {ctx.command}: {error}")
