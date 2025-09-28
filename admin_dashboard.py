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

## 2. Create `admin_dashboard.py` (Secure Blueprint)

This new file contains the core security logic. You must set two new environment variables on your hosting platform: `ADMIN_USER` and `ADMIN_PASS`. Without them, the login will fail, and the dashboard is inaccessible.

```python:GND Manager Admin Dashboard:admin_dashboard.py
import os
import json
import time
from flask import Blueprint, render_template_string, request
from flask_httpauth import HTTPBasicAuth
from datetime import datetime, timedelta

# Import necessary components and constants from the bot logic module
# This allows the web server to access the bot's global data and file constants.
from .bot_logic import MOD_LOGS_FILE, METRICS_FILE, bot, BOT_START_TIME, ACTIVE_CHATTERS 

# --- FLASK BLUEPRINT & AUTHENTICATION SETUP ---

admin_bp = Blueprint('admin', __name__)
auth = HTTPBasicAuth()

# Credentials sourced from environment variables for security
ADMIN_USER = os.getenv('ADMIN_USER')
ADMIN_PASS = os.getenv('ADMIN_PASS')

# --- DATA ACCESS HELPERS ---

def load_json(filepath):
    """Safely loads JSON data from a file on disk."""
    if not os.path.exists(filepath):
        return {}
    try:
        # The web process needs to read the file saved by the bot thread
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # Return empty object if file is corrupt or unreadable
        return {}
    
def get_bot_commands_doc():
    """Dynamically builds a list of staff commands for documentation."""
    commands_list = []
    # Loop through the bot's command list (from the bot_logic import)
    for command in bot.commands:
        # Filter for commands with help text and the moderator check
        if command.help and any(check.__name__ == 'is_moderator' for check in command.checks):
            commands_list.append({
                'name': command.name,
                'usage': f"!{command.name} {command.signature or ''}",
                'description': command.help.replace('[STAFF]', '').replace('[ADMIN]', '').strip()
            })
    return commands_list


# --- AUTHENTICATION LOGIC ---

@auth.verify_password
def verify_password(username, password):
    """Verifies the username and password against the environment variables."""
    if not ADMIN_USER or not ADMIN_PASS:
        # Crucial security check: Fails closed if credentials aren't set
        print("SECURITY ALERT: ADMIN_USER or ADMIN_PASS environment variables are not set. Access denied.")
        return False
        
    return username == ADMIN_USER and password == ADMIN_PASS

# --- DASHBOARD ROUTES ---

@admin_bp.route('/', methods=['GET', 'POST'])
@auth.login_required # This decorator forces Basic Authentication
def admin_home():
    """
    The main admin dashboard page, displaying health and core metrics.
    """
    
    # 1. Load Data from Disk (Latest metrics and logs)
    mod_logs_data = load_json(MOD_LOGS_FILE)
    metrics_data = load_json(METRICS_FILE)
    
    # 2. Uptime/Health Data
    uptime_seconds = int(time.time() - BOT_START_TIME)
    uptime_display = str(timedelta(seconds=uptime_seconds)).split('.')[0] # Remove milliseconds
    latency_ms = round(bot.latency * 1000) if bot.is_ready() else "N/A"
    
    # 3. Core Metrics Snapshot
    total_logs = len(mod_logs_data.get('logs', []))
    summary = metrics_data.get('monthly_summary', {})
    
    # 4. Search Functionality (Minimal implementation for Step 2)
    search_results = None
    if request.method == 'POST':
        target_id = request.form.get('target_id')
        if target_id and total_logs > 0:
            user_logs = [log for log in mod_logs_data['logs'] if log['target_id'] == target_id]
            search_results = user_logs[:10]
        
    # 5. Log Summary (Last 5 actions)
    log_summary = mod_logs_data.get('logs', [])[:5]
    
    # 6. Command Documentation
    command_docs = get_bot_commands_doc()
    
    # Simple, functional HTML using f-strings and inline CSS (for Step 2 simplicity)
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>GND Manager Admin Dashboard</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 0; background: #eef2f6; color: #333; }}
            .header {{ background: #2c3e50; color: white; padding: 15px 40px; border-bottom: 5px solid #3498db; }}
            .container {{ max-width: 1200px; margin: 30px auto; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: grid; grid-template-columns: 1fr 2fr; gap: 30px; }}
            .card {{ background: #f9f9f9; padding: 20px; border-radius: 6px; border-left: 5px solid #bdc3c7; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px; }}
            .metric-card {{ background: #ecf0f1; padding: 15px; border-radius: 4px; text-align: center; }}
            .metric-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
            h2 {{ border-bottom: 1px solid #eee; padding-bottom: 5px; color: #34495e; }}
            .log-item {{ border-bottom: 1px dotted #ddd; padding: 10px 0; font-size: 0.9em; }}
            form {{ margin-bottom: 20px; }}
            input[type="text"] {{ padding: 10px; width: 60%; border: 1px solid #ddd; border-radius: 4px; }}
            input[type="submit"] {{ padding: 10px 15px; background: #2ecc71; color: white; border: none; border-radius: 4px; cursor: pointer; }}
            .commands-list {{ margin-top: 10px; }}
            .command {{ background: #f0f8ff; padding: 10px; margin-bottom: 8px; border-radius: 4px; border-left: 3px solid #3498db; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🛡️ GND Manager Administration</h1>
        </div>
        <div class="container">
            <div class="sidebar">
                <h2>Bot Health</h2>
                <div class="card" style="border-left-color: {'#2ecc71' if latency_ms != 'N/A' and latency_ms < 500 else '#f1c40f'};">
                    <p><strong>Status:</strong> <span style="color: {'#2ecc71' if latency_ms != 'N/A' else '#f1c40f'};">{'ONLINE' if latency_ms != 'N/A' else 'STARTING'}</span></p>
                    <p><strong>Uptime:</strong> {uptime_display}</p>
                    <p><strong>Latency:</strong> {latency_ms} ms</p>
                </div>
                
                <h2>Core Metrics</h2>
                <div class="metric-grid">
                    <div class="metric-card"><div class="metric-value">{total_logs}</div><small>Total Logged Actions</small></div>
                    <div class="metric-card"><div class="metric-value">{summary.get('total_bans', 0)}</div><small>Bans This Month</small></div>
                    <div class="metric-card"><div class="metric-value">{len(ACTIVE_CHATTERS)}</div><small>Active Chatters</small></div>
                </div>

                <h2>Admin Commands Reference</h2>
                <div class="commands-list">
                    {
                        ''.join([
                            f"<div class='command'><strong>!{cmd['name']}</strong> <code>{cmd['usage']}</code><br><small>{cmd['description']}</small></div>"
                            for cmd in command_docs
                        ])
                    }
                </div>
            </div>

            <div class="main-content">
                <h2>Moderation Log Search (User ID)</h2>
                <form method="POST">
                    <input type="text" name="target_id" placeholder="Enter Discord User ID (e.g., 1234567890)" required>
                    <input type="submit" value="Search Record">
                </form>

                {'<div class="card" style="border-left-color: #e74c3c;"><h3>No Records Found</h3></div>' if request.method == 'POST' and not search_results else ''}
                
                {
                    f'<h2>Record for ID: {request.form.get("target_id")} ({len(search_results)} Logs)</h2>' if search_results else ''
                }
                
                {''.join([
                    f'<div class="log-item"><strong>{log["action"]}</strong> by {log["moderator_id"]}<br>Reason: {log["reason"]}<br><small>{datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")}</small></div>'
                    for log in search_results
                ]) if search_results else ''}

                <h2>Recent Log Summary</h2>
                {
                    ''.join([
                        f'<div class="log-item"><strong>{log["action"]}</strong> on ID {log["target_id"]}<br>Reason: {log["reason"]}<br><small>{datetime.fromisoformat(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")}</small></div>'
                        for log in log_summary
                    ])
                }
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_content)
```eof
