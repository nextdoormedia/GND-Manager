import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import random
import time
import json
import asyncio # New import for running the bot concurrently

# --- DATABASE SETUP (File-Based for PythonAnywhere/Render) ---
# We use a simple JSON file to store Vibe data.
DATABASE_FILE = "vibe_data.json"

def load_data():
    """Loads Vibe data from the JSON file."""
    if os.path.exists(DATABASE_FILE):
        # Check if the file is empty before trying to load JSON
        if os.path.getsize(DATABASE_FILE) > 0:
            try:
                with open(DATABASE_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                # If the file content is invalid JSON, return an empty dictionary
                print("Error loading JSON data. Starting with empty data.")
                return {}
    return {}

def save_data(data):
    """Saves Vibe data to the JSON file."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load the initial data.
vibe_data = load_data()
# Dictionary to track the last time a user was given XP (for cooldown)
last_vibe_time = {}
COOLDOWN_SECONDS = 15 # The required 15-second cooldown

# --- END DATABASE SETUP ---

# --- FLASK WEB SERVER SETUP (Required for 24/7 Hosting on Render) ---
# Flask needs to run in the foreground (main thread) for Render's Web Service to stay active.
app = Flask(__name__)

@app.route('/')
def home():
    """Simple route to satisfy Render's health check."""
    # We check if the bot is actually logged in before saying it's online
    if bot.is_ready():
        return "Housemate Ryker is online and managing the neighborhood!"
    else:
        return "Housemate Ryker is initializing...", 503 # Service Unavailable

def run_flask_server():
    """Function to run the Flask app using a simple server binding."""
    # We must use gunicorn in the Procfile, but this function is kept for completeness.
    # The actual running is handled by gunicorn in the main process loop below.
    pass

# --- END FLASK WEB SERVER SETUP ---

# Enable privileged intents for the bot.
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Create the bot instance.
bot = commands.Bot(command_prefix='!', intents=intents)

# --- BOT EVENTS ---

# This function runs the Discord bot in a separate thread.
def start_bot():
    """Starts the Discord bot connection."""
    # Get the token from the environment variables (set on Render)
    token = os.getenv('DISCORD_TOKEN')
    if token is None:
        print("ERROR: DISCORD_TOKEN environment variable is not set. Bot cannot log in.")
    else:
        # We must use run_in_thread=False since we are managing the thread manually
        bot.run(token)

@bot.event
async def on_ready():
    """Runs when the bot has successfully connected to Discord."""
    print(f'Successfully logged in as {bot.user.name} ({bot.user.id})')
    print('Housemate Ryker is ready to manage the neighborhood.')
    # Set the bot's status to show it's working
    await bot.change_presence(activity=discord.Game(name="Managing the Neighborhood | !rank"))


@bot.event
async def on_member_join(member):
    """Greets new members and directs them to the rules."""
    # Welcome Channel ID: 1420121916404007136 (Replace with yours if different)
    welcome_channel = bot.get_channel(1420121916404007136)
    rules_channel = bot.get_channel(1420122298391990376) # Rules Channel ID

    if welcome_channel:
        try:
            embed = discord.Embed(
                title=f"Welcome to the Neighborhood, {member.name}!",
                description=f"We're thrilled to have you move in. To get full access to the server, you must first agree to the rules.",
                color=discord.Color.green()
            )
            embed.add_field(name="ACTION REQUIRED:", value=f"Please head over to {rules_channel.mention} and react to the pinned message to receive your 'Member' role and unlock the full server!", inline=False)

            # Check if the channel is a text channel before trying to send
            if isinstance(welcome_channel, discord.TextChannel):
                await welcome_channel.send(f"Welcome, {member.mention}!", embed=embed)
        except Exception as e:
            print(f"Error sending welcome message: {e}")


@bot.event
async def on_raw_reaction_add(payload):
    """Handles the reaction-based verification."""
    # Rules Channel ID: 1420122298391990376
    # Rule Message ID: 1420130243645276262
    RULES_CHANNEL_ID = 1420122298391990376
    RULES_MESSAGE_ID = 1420130243645276262
    VERIFICATION_EMOJI = '✅' # Green checkmark

    # Check if the reaction is on the specific rules message and is the correct emoji
    if payload.channel_id == RULES_CHANNEL_ID and payload.message_id == RULES_MESSAGE_ID and str(payload.emoji) == VERIFICATION_EMOJI:

        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id)
        if not member or member.bot:
            return

        # Find the "Member" role (create this role in Discord if it doesn't exist!)
        member_role = discord.utils.get(guild.roles, name="Member")

        if member_role and member_role not in member.roles:
            try:
                # Assign the role
                await member.add_roles(member_role)
                print(f"Verified and assigned 'Member' role to {member.name}")

                # Send a welcome DM (This is the one-time message about the Vibe system)
                try:
                    await member.send(
                        f"🎉 Welcome to the fully unlocked Neighborhood! As a new member, you've been granted the 'Member' role.\n\n"
                        f"**New Feature:** This server uses the **Vibe System**! You earn **Vibe** (XP) just by chatting (once every {COOLDOWN_SECONDS} seconds). "
                        f"Earn Vibe to **Move Up The Block** and unlock cool cosmetic roles like 'Resident' and 'Block Captain'.\n\n"
                        f"Check your progress anytime with the `!rank` command!"
                    )
                except discord.Forbidden:
                    # Fails if user has DMs disabled
                    print(f"Could not send welcome DM to {member.name}. User has DMs disabled.")

            except discord.Forbidden:
                print(f"Bot lacks permissions to add the 'Member' role to {member.name}.")
            except Exception as e:
                print(f"An unexpected error occurred during verification: {e}")


@bot.event
async def on_message(message):
    """Handles Vibe (XP) granting and commands."""
    if message.author.bot or not message.guild:
        return

    user_id = str(message.author.id)
    current_time = time.time()

    # --- VIBE COOLDOWN CHECK ---
    if user_id in last_vibe_time:
        if current_time - last_vibe_time[user_id] < COOLDOWN_SECONDS:
            await bot.process_commands(message)
            return

    # --- VIBE GRANTING ---
    # Give a small, random amount of Vibe (XP)
    vibe_to_add = random.randint(1, 3)

    if user_id not in vibe_data:
        vibe_data[user_id] = {"vibe": 0, "level": 1, "name": message.author.name}

    vibe_data[user_id]["vibe"] += vibe_to_add
    vibe_data[user_id]["name"] = message.author.name # Update name in case of change
    last_vibe_time[user_id] = current_time

    # Save the data (we save frequently to ensure persistence)
    save_data(vibe_data)

    # --- LEVELING CHECK (Moving Up The Block) ---
    await check_vibe_rank(message.author, vibe_data[user_id]["vibe"])

    # Process any bot commands in the message
    await bot.process_commands(message)


async def check_vibe_rank(member, current_vibe):
    """Checks the member's current Vibe and updates their role."""

    # Define the Vibe thresholds and corresponding role names
    VIBE_RANKS = {
        1000: "Block Captain",
        500: "Housemate",
        250: "Resident",
        100: "Familiar Face",
        0: "New Neighbor"
    }

    # Determine the target role based on current Vibe
    target_rank_name = "New Neighbor"
    for threshold, name in sorted(VIBE_RANKS.items(), reverse=True):
        if current_vibe >= threshold:
            target_rank_name = name
            break

    target_role = discord.utils.get(member.guild.roles, name=target_rank_name)

    if not target_role:
        print(f"WARNING: Target role '{target_rank_name}' not found in server.")
        return

    # List of all Vibe cosmetic roles (to remove old ones)
    all_vibe_roles = [
        discord.utils.get(member.guild.roles, name=name)
        for name in VIBE_RANKS.values()
    ]
    # Filter out None values and the target role
    roles_to_remove = [role for role in all_vibe_roles if role and role != target_role and role in member.roles]

    if target_role not in member.roles:
        try:
            # Add the new target role
            await member.add_roles(target_role)

            # Remove all lower/obsolete Vibe roles
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)

            # Notify the user in the channel where they achieved the rank
            await member.send(
                f"🎉 Congratulations, you're **Moving Up The Block**! You are now a **{target_rank_name}**!"
            )
            print(f"{member.name} promoted to {target_rank_name}")

        except discord.Forbidden:
            print(f"Bot lacks permissions to manage roles for {member.name}.")
        except Exception as e:
            print(f"An error occurred during role update for {member.name}: {e}")


# --- BOT COMMANDS ---

# Command to check a user's current rank and Vibe.
@bot.command(name='rank')
async def rank(ctx):
    """Shows the user's current Vibe, rank, and progress."""
    user_id = str(ctx.author.id)

    if user_id not in vibe_data:
        vibe = 0
    else:
        vibe = vibe_data[user_id]["vibe"]

    # Determine rank name based on Vibe thresholds
    rank_name = "New Neighbor"
    if vibe >= 100: rank_name = "Familiar Face"
    if vibe >= 250: rank_name = "Resident"
    if vibe >= 500: rank_name = "Housemate"
    if vibe >= 1000: rank_name = "Block Captain"

    embed = discord.Embed(
        title=f"The Neighborhood Status of {ctx.author.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Vibe", value=f"**{vibe}** Vibe", inline=True)
    embed.add_field(name="Rank", value=f"**{rank_name}**", inline=True)
    embed.set_footer(text="Keep chatting to earn Vibe and Move Up The Block!")
    await ctx.send(embed=embed)


# Command to show the leaderboard.
@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """Shows the top 10 most active members."""
    leaderboard_data = {}
    for user_id in vibe_data.keys():
        try:
            # Use the stored name if available, otherwise fetch the user
            user_name = vibe_data[user_id].get("name", f"User_{user_id}")
            vibe_count = vibe_data[user_id]["vibe"]
            leaderboard_data[user_name] = vibe_count
        except (ValueError, KeyError):
            continue

    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)

    leaderboard_string = ""
    for i, (name, vibe) in enumerate(sorted_leaderboard[:10]):
        # Use simple bold markdown for ranking
        leaderboard_string += f"**{i+1}.** {name} - {vibe} Vibe\n"

    if not leaderboard_string:
         leaderboard_string = "No Vibe earned yet! Start chatting!"

    embed = discord.Embed(
        title="🏆 Top 10 Most Active Neighbors (Vibe Leaderboard)",
        description=leaderboard_string,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)


# --- APPLICATION ENTRY POINT ---

if __name__ == '__main__':
    # 1. Start the Discord Bot in a background thread
    # We do this first so the bot begins connecting immediately.
    print("Starting Discord Bot thread...")
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    # 2. Run the Flask Web Server in the main process
    # This keeps the main application running, satisfying Render's Web Service requirement.
    # We use gunicorn to run this app (as defined in the Procfile).
    # The actual gunicorn execution is external: gunicorn housemate_ryker:app
    # If testing locally without gunicorn:
    if os.getenv('DISCORD_TOKEN') is not None and not os.getenv('GUNICORN_PROCESS'):
        print("Running Flask server locally (use gunicorn for production)...")
        app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080), debug=False)
