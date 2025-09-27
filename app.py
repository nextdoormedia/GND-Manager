import os
from flask import Flask
import threading
# Ensure bot_logic.py is in the same directory for this import to work
from bot_logic import bot 

app = Flask(__name__)

# --- START BOT IN A SEPARATE THREAD ---

def start_discord_bot():
    """Function to run the Discord bot's blocking client method."""
    print("--- Housemate Ryker: Starting Discord Bot Thread ---")
    try:
        # bot.run() is a blocking call that handles the event loop.
        # It MUST be run in its own thread/process.
        bot.run(os.getenv('DISCORD_TOKEN'), reconnect=True)
    except Exception as e:
        # If this fires, it means the bot failed to log in (usually bad token) 
        # or crashed due to a critical error.
        print(f"FATAL ERROR IN DISCORD BOT THREAD: {e}")

# The code below runs once when the Gunicorn worker process starts.
print("--- Gunicorn Worker Booted, Initiating Bot Startup ---")
discord_thread = threading.Thread(target=start_discord_bot)
# Setting to daemon=True allows the Flask server to exit cleanly if necessary,
# but it mainly ensures the bot thread runs in the background.
discord_thread.daemon = True 
discord_thread.start()


# --- FLASK WEB SERVER (For Render Health Check) ---

@app.route('/')
def home():
    # Health check endpoint required by Render's Web Service model
    return "Housemate Ryker is online and managing the neighborhood."

# The if __name__ == '__main__': block is ignored by Gunicorn in production.