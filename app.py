import os
from flask import Flask
import asyncio
# Ensure bot_logic.py is in the same directory for this import to work
from bot_logic import bot 

app = Flask(__name__)

# Global flag to ensure bot starts only once per Gunicorn worker process
bot_started = False

# The modern, non-deprecated way to execute code that needs to run once.
# We use a flag inside this function to achieve the "run once" behavior.
@app.before_request
def launch_bot():
    global bot_started
    # Check the flag. If the bot hasn't started in this process, start it.
    if not bot_started:
        print("Launching Discord Bot client via asyncio...")
        
        # Get the event loop and safely schedule the bot start as a background task.
        loop = asyncio.get_event_loop()
        
        # The bot's token is read from the environment variable set on Render.
        loop.create_task(bot.start(os.getenv('DISCORD_TOKEN')))
        
        # Set the flag so this block never runs again in this worker process.
        bot_started = True

@app.route('/')
def home():
    # Health check endpoint required by Render's Web Service model
    return "Housemate Ryker is online and managing the neighborhood."

if __name__ == '__main__':
    # For local testing only (Gunicorn ignores this block)
    if os.getenv('DISCORD_TOKEN'):
        app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
    else:
        print("ERROR: DISCORD_TOKEN environment variable not set.")