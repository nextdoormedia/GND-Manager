
import os
from flask import Flask
import threading
# Ensure bot_logic.py is in the same directory for this import to work
from bot_logic import bot 
from admin_dashboard import admin_bp # NEW: Import the admin blueprint

app = Flask(__name__)

# NEW: Register the admin blueprint and protect it behind the /admin URL prefix.
app.register_blueprint(admin_bp, url_prefix='/admin')

# --- START BOT IN A SEPARATE THREAD (For 24/7 Hosting) ---

def start_discord_bot():
    """
    Function to run the Discord bot's blocking client method.
    This must be run in a separate thread/process from the Flask web server.
    """
    # Updated: Changed name reference from "Housemate Ryker" to "GND Manager"
    print("--- GND Manager: Starting Discord Bot Thread ---")
    try:
        # bot.run() is a blocking call that handles the event loop.
        # It MUST be run in its own thread/process.
        # DISCORD_TOKEN is retrieved from environment variables set on the hosting platform.
        bot.run(os.getenv('DISCORD_TOKEN'), reconnect=True)
    except Exception as e:
        # Catch critical errors like bad token or connection failure
        print(f"FATAL ERROR IN DISCORD BOT THREAD: {e}")

# This code runs once when the Gunicorn worker process starts.
print("--- Gunicorn Worker Booted, Initiating Bot Startup ---")
discord_thread = threading.Thread(target=start_discord_bot)
# Setting to daemon=True ensures the thread exits cleanly when the main process does.
discord_thread.daemon = True 
discord_thread.start()


# --- FLASK WEB SERVER (For Health Check) ---

@app.route('/')
def home():
    """
    Simple health check endpoint required by the Web Service hosting model.
    If this endpoint returns successfully, the host knows the app is alive.
    """
    # Updated: Changed name reference in the health check message
    return "GND Manager is online and managing the neighborhood."

if __name__ == '__main__':
    # This block is for local testing only (Gunicorn ignores this in production).
    if os.getenv('DISCORD_TOKEN'):
        print("Running Flask server locally...")
        app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
    else:
        print("ERROR: DISCORD_TOKEN environment variable not set. Please set it for local testing.")
```eof

