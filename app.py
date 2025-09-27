import os
from flask import Flask
import asyncio
from bot_logic import bot # Import the bot instance from the logic file

app = Flask(__name__)

# This function runs when the Flask server starts, which is managed by Gunicorn.
@app.before_first_request
def launch_bot():
    print("Launching Discord Bot client via asyncio...")
    # Get the event loop and safely start the bot as a background task.
    loop = asyncio.get_event_loop()
    # The bot's token is read from the environment variable set on Render.
    loop.create_task(bot.start(os.getenv('DISCORD_TOKEN')))

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
