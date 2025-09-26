import discord
from discord.ext import commands
import os
import random
import time
import json
import typing as t
from flask import Flask
from threading import Thread

# --- DATABASE SETUP (File-based Vibe tracking) ---
DATABASE_FILE = "vibe_data.json"

def load_data():
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("WARNING: Vibe data file is corrupt. Starting fresh.")
            return {}
    return {}

def save_data(data):
    # Ensure directory exists before writing (good practice for Render)
    os.makedirs(os.path.dirname(DATABASE_FILE) or '.', exist_ok=True)
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Load the initial data.
vibe_data = load_data()
# --- END DATABASE SETUP ---

# --- BOT SETUP (Start in a separate thread for Render) ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Threading function to run the Discord Bot
def start_bot():
    try:
        # This will run the bot in the background thread
        bot.run(os.environ['DISCORD_TOKEN'])
    except discord.errors.LoginFailure as e:
        print(f"ERROR: Failed to log in. Check DISCORD_TOKEN environment variable. {e}")

# --- DISCORD BOT LOGIC (Remains the same) ---

@bot.event
async def on_ready():
    if bot.user:
        print(f'Logged in as {bot.user.name} ({bot.user.id})')
        print('Housemate Ryker is fully operational.')
        print('------')

@bot.event
async def on_member_join(member):
    welcome_channel_id = 1420121916404007136
    rules_channel_id = 1420122298391990376

    welcome_channel = bot.get_channel(welcome_channel_id)
    rules_channel = bot.get_channel(rules_channel_id)

    if welcome_channel and isinstance(welcome_channel, discord.TextChannel) and rules_channel and isinstance(rules_channel, discord.TextChannel):
        welcome_messages = [
            f"Look who just moved in next door! Welcome to the squad, {member.mention}! 😉 We're so glad you're here. Kick back, grab a drink, and check out our #server-rules before you start chatting.",
            f"Hey there, {member.mention}! Glad you found your way here. Settle in, get to know the neighbors, and check out the #role-guide to get started.",
            f"Another awesome neighbor just joined! Welcome, {member.mention}! The door's always open here. We're happy to have you.",
            f"A new face in the neighborhood! Welcome to the crew, {member.mention}. We've been expecting you 😉",
            f"Who's that? Oh, it's a new member! Welcome, {member.mention}! The fridge is stocked and the vibes are chill. Check out the #role-guide to get comfy.",
            f"Someone new just moved in! Welcome, {member.mention}! We're happy you're here. Go ahead and introduce yourself.",
            f"Hey, {member.mention}, what's up? Welcome to the GuysNextDoor community! We're glad you're here. Kick back, and make yourself at home.",
            f"Welcome, {member.mention}! Housemate Ryker here. Just wanted to say we're happy to have you. Hope you like it here.",
            f"Hey, {member.mention}! The party's here. Welcome to our community. Grab a seat, and get to know the neighbors.",
            f"Oh, hey there, {member.mention}! It's good to see you. Welcome to the house! Hope you brought some good vibes with you."
        ]

        welcome_message = random.choice(welcome_messages)
        await welcome_channel.send(welcome_message)
        await rules_channel.send(f"Hey {member.mention}, to get full access to the server, please read and react to the pinned message in this channel.")


@bot.event
async def on_raw_reaction_add(payload):
    rules_message_id = 1420130243645276262
    if payload.message_id == rules_message_id:
        guild = bot.get_guild(payload.guild_id)
        if guild:
            member = guild.get_member(payload.user_id)
            if member and not member.bot:
                member_role = discord.utils.get(guild.roles, name="Member")
                if member_role:
                    await member.add_roles(member_role)
                    try:
                        await member.send(f"You've been granted the Member role! Welcome to the house, you can now see the rest of the server.")
                    except discord.Forbidden:
                        print(f"Could not send DM to {member.name}.")

@bot.event
async def on_message(message):
    if message.author.bot or not isinstance(message.channel, discord.TextChannel):
        return

    cooldown_time = 15
    user_id = str(message.author.id)
    current_time = time.time()

    if user_id in vibe_data and "last_message_time" in vibe_data[user_id] and (current_time - vibe_data[user_id]["last_message_time"]) < cooldown_time:
        return

    if user_id not in vibe_data:
        vibe_data[user_id] = {"vibe": 0, "last_message_time": 0, "first_vibe_message_sent": False}

    xp_to_add = random.randint(1, 3)
    vibe_data[user_id]["vibe"] += xp_to_add
    vibe_data[user_id]["last_message_time"] = current_time
    save_data(vibe_data)

    if not vibe_data[user_id]["first_vibe_message_sent"]:
        try:
            await message.author.send(
                f"Hey, {message.author.name}! As a new neighbor, you've started building your Vibe in the community. You earn Vibe just by chatting! The more Vibe you have, the more you'll move up the block and earn a new cosmetic role. Check your status with `!rank` and see who's at the top with `!leaderboard`."
            )
            vibe_data[user_id]["first_vibe_message_sent"] = True
            save_data(vibe_data)
        except discord.errors.Forbidden:
            print(f"Could not send a DM to {message.author.name}.")

    vibe = vibe_data[user_id]["vibe"]

    roles = {
        "New Neighbor": 0,
        "Familiar Face": 100,
        "Resident": 250,
        "Housemate": 500,
        "Block Captain": 1000
    }

    for role_name, required_vibe in roles.items():
        if vibe >= required_vibe:
            role = discord.utils.get(message.guild.roles, name=role_name)
            if role and role not in message.author.roles:
                for old_role in message.author.roles:
                    if old_role.name in roles:
                        await message.author.remove_roles(old_role)

                await message.author.add_roles(role)
                await message.channel.send(f"🎉 **Congratulations, {message.author.mention}!** You've moved up the block and are now a **{role_name}**! Your Vibe is at **{vibe}**.")

    await bot.process_commands(message)

@bot.command(name='rank')
async def rank(ctx):
    user_id = str(ctx.author.id)
    if user_id not in vibe_data:
        await ctx.send("You haven't earned any Vibe yet. Start chatting to get some!")
        return

    vibe = vibe_data[user_id]["vibe"]

    rank_name = "New Neighbor"
    if vibe >= 100: rank_name = "Familiar Face"
    if vibe >= 250: rank_name = "Resident"
    if vibe >= 500: rank_name = "Housemate"
    if vibe >= 1000: rank_name = "Block Captain"

    embed = discord.Embed(title=f"The Neighborhood Status of {ctx.author.name}", color=discord.Color.blue())
    embed.add_field(name="Vibe", value=vibe, inline=True)
    embed.add_field(name="Rank", value=rank_name, inline=True)
    await ctx.send(embed=embed)

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    leaderboard_data = {}
    for user_id in vibe_data.keys():
        try:
            # Note: bot.get_user requires the bot to be in the server to retrieve user data
            user = bot.get_user(int(user_id))
            if user:
                leaderboard_data[user.name] = vibe_data[user_id]["vibe"]
        except (ValueError, KeyError):
            continue

    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda item: item[1], reverse=True)

    leaderboard_string = ""
    for i, (name, vibe) in enumerate(sorted_leaderboard[:10]):
        leaderboard_string += f"{i+1}. {name} - {vibe} Vibe\n"

    embed = discord.Embed(title="Top 10 Most Active Neighbors", color=discord.Color.gold())
    embed.description = leaderboard_string
    await ctx.send(embed=embed)

# --- WEB SERVER SETUP (Starts the Bot and then runs the Flask app) ---
app = Flask(__name__)

@app.route('/')
def home():
    if bot.is_ready():
        return "Housemate Ryker is running and ready for duty!"
    else:
        return "Housemate Ryker is starting up...", 503

# --- FINAL EXECUTION ---
# 1. Start the Discord bot in a background thread.
# 2. Start the Flask server in the main thread (this is what Gunicorn controls).
if __name__ == '__main__':
    start_bot_thread = Thread(target=start_bot)
    start_bot_thread.start()
