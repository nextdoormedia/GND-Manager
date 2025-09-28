import os
from flask import Flask, render_template_string
import threading
from bot_logic import bot 
from admin_dashboard import admin_bp 

app = Flask(__name__)

# Register the admin blueprint and protect it behind the /admin URL prefix.
app.register_blueprint(admin_bp, url_prefix='/admin')

# --- START BOT IN A SEPARate THREAD (For 24/7 Hosting) ---

def start_discord_bot():
    """
    Function to run the Discord bot's blocking client method.
    """
    print("--- GND Manager: Starting Discord Bot Thread ---")
    try:
        # DISCORD_TOKEN is retrieved from environment variables set on the hosting platform.
        bot.run(os.getenv('DISCORD_TOKEN'), reconnect=True)
    except Exception as e:
        print(f"FATAL ERROR IN DISCORD BOT THREAD: {e}")

print("--- Gunicorn Worker Booted, Initiating Bot Startup ---")
discord_thread = threading.Thread(target=start_discord_bot)
discord_thread.daemon = True 
discord_thread.start()


# --- FLASK WEB SERVER (Updated Root Landing Page) ---

@app.route('/')
def home():
    """
    The member-facing landing page for the GND Manager system, 
    updated to reflect the security and utility focus.
    """
    
    # We use a placeholder for the invite link here for deployment safety. 
    DISCORD_INVITE_LINK = "https://discord.gg/YourInviteCode" 
    
    is_online = bot.is_ready()
    status_text = "Operational" if is_online else "Starting Up"
    status_color = "bg-green-500" if is_online else "bg-yellow-500"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GND Manager - GUYSNEXTDOOR</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap');
            body {{ 
                font-family: 'Inter', sans-serif; 
                background: #111827; 
            }}
        </style>
    </head>
    <body class="min-h-screen flex items-center justify-center p-4">
        <div class="max-w-xl w-full bg-gray-800 text-white p-8 md:p-10 rounded-xl shadow-2xl border-t-8 border-red-600 space-y-8">
            
            <!-- Header & Status -->
            <div class="text-center space-y-3">
                <h1 class="text-4xl font-extrabold text-red-500 tracking-tight">
                    GUYSNEXTDOOR
                </h1>
                <p class="text-xl text-gray-300">
                    The official home of the **GND Manager**, your 24/7 administrative utility.
                </p>
                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium {status_color} text-white">
                    <svg class="w-2 h-2 mr-1.5" fill="currentColor" viewBox="0 0 8 8">
                        <circle cx="4" cy="4" r="3" />
                    </svg>
                    System Status: {status_text} | Dedicated Web Service
                </span>
            </div>

            <!-- Call to Action -->
            <div class="text-center">
                <a href="{DISCORD_INVITE_LINK}" target="_blank"
                   class="inline-block w-full sm:w-auto px-8 py-3 text-lg font-bold rounded-lg transition duration-300 bg-indigo-600 hover:bg-indigo-700 shadow-xl hover:shadow-indigo-500/50">
                    Join the Neighborhood Discord 🏠
                </a>
            </div>
            
            <hr class="border-gray-700">

            <!-- Core Administrative Features -->
            <div class="space-y-4">
                <h2 class="text-2xl font-semibold text-gray-200">🛡️ Core Administrative Focus</h2>
                <ul class="space-y-3 text-gray-400">
                    <li class="flex items-start">
                        <span class="text-red-500 mr-2 mt-0.5">📜</span>
                        <p><strong>Total Accountability:</strong> All disciplinary actions are logged to the **Permanent Record** for audit and security purposes.</p>
                    </li>
                    <li class="flex items-start">
                        <span class="text-red-500 mr-2 mt-0.5">🔨</span>
                        <p><strong>Auto-Eviction Enforcement:</strong> Instantly re-bans any user attempting to evade a prior permanent ban.</p>
                    </li>
                    <li class="flex items-start">
                        <span class="text-red-500 mr-2 mt-0.5">🔍</span>
                        <p><strong>Background Checks:</strong> Staff can instantly look up a user's full disciplinary history.</p>
                    </li>
                    <li class="flex items-start">
                        <span class="text-red-500 mr-2 mt-0.5">🚨</span>
                        <p><strong>Neighborhood Watch:</strong> Automatic content filters prevent spam and unauthorized promotion.</p>
                    </li>
                </ul>
            </div>
            
            <hr class="border-gray-700">
            
            <!-- User Utility Features -->
            <div class="space-y-4">
                <h2 class="text-2xl font-semibold text-gray-200">⚙️ Member Utilities & Information</h2>
                <ul class="space-y-3 text-gray-400 grid md:grid-cols-2">
                    <li class="flex items-start">
                        <span class="text-indigo-400 mr-2 mt-0.5">📝</span>
                        <p><strong>The Lease Agreement:</strong> Use `!rules` for essential guidelines.</p>
                    </li>
                    <li class="flex items-start">
                        <span class="text-indigo-400 mr-2 mt-0.5">🗓️</span>
                        <p><strong>Weekly Rota:</strong> Use `!schedule` for content and event times.</p>
                    </li>
                    <li class="flex items-start">
                        <span class="text-indigo-400 mr-2 mt-0.5">🔑</span>
                        <p><strong>The Keyring:</strong> Use `!links` for all official platforms.</p>
                    </li>
                    <li class="flex items-start">
                        <span class="text-indigo-400 mr-2 mt-0.5">🤫</span>
                        <p><strong>Tattletale Tool:</strong> Use `!report` for discreet submissions.</p>
                    </li>
                </ul>
            </div>


            <hr class="border-gray-700">

            <!-- Legal and Important Notice -->
            <div class="text-center text-sm text-gray-500 space-y-2">
                <p class="text-red-400 font-bold">⚠️ AGE RESTRICTION: ALL GND PLATFORMS ARE STRICTLY 18+</p>
                <p>
                    <!-- IMPORTANT: Using the specific legal links from the bot_logic snippet/markdown files -->
                    <a href="https://guysnextdoor.netlify.app/legal/policy" target="_blank" class="hover:text-red-500 transition">Privacy Policy</a> | 
                    <a href="https://guysnextdoor.netlify.app/legal/tos" target="_blank" class="hover:text-red-500 transition">Terms of Service</a>
                </p>
                <!-- Admin link is discreetly placed for staff access -->
                <p>Staff: <a href="/admin" class="hover:text-red-500 transition text-gray-600 font-medium border-b border-dotted border-gray-600">Admin Portal Login</a></p>
            </div>
            
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_content)

if __name__ == '__main__':
    # This block is for local testing only (Gunicorn ignores this in production).
    if os.getenv('DISCORD_TOKEN'):
        print("Running Flask server locally...")
        app.run(host='0.0.0.0', port=os.environ.get('PORT', 5000))
    else:
        print("ERROR: DISCORD_TOKEN environment variable not set. Please set it for local testing.")