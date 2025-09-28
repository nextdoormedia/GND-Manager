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
    Function to run the Discord bot's blocking client method safely in a thread.
    
    NOTE: This uses bot.start/loop.run_until_complete to safely run the bot in 
    a separate thread, avoiding the fatal "RuntimeError: can't register atexit after shutdown".
    """
    print("--- GND Manager: Starting Discord Bot Thread -----")
    try:
        # 1. Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 2. Use bot.start() to run the bot and run_until_complete to block the thread
        # The reconnect=True argument is now passed to bot.start()
        loop.run_until_complete(bot.start(os.getenv('DISCORD_TOKEN'), reconnect=True))

    except Exception as e:
        print(f"FATAL ERROR IN DISCORD BOT THREAD: {e}")

print("--- Gunicorn Worker Booted, Initiating Bot Startup ---")
discord_thread = threading.Thread(target=start_discord_bot)
discord_thread.daemon = True 
discord_thread.start()


# --- FLASK WEB SERVER (Cohesive Root Landing Page) ---

@app.route('/')
def home():
    """
    The member-facing landing page for the GND Manager system, 
    updated to use the primary Red branding and scrolling marquee.
    """
    
    DISCORD_INVITE_LINK = "https://discord.gg/EKekh3wHYQ" 
    
    # Static link data (these links were taken from your bot_logic.py snippet)
    GND_LINKS = [
        {"name": "Main Website", "url": "https://guysnextdoor.netlify.app"},
        {"name": "Chaturbate", "url": "https://chaturbate.com/hotcockjock99"},
        {"name": "PornHub", "url": "https://pornhub.com/model/guysnextdoor"},
    ]
    
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
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
            
            /* Match Main Website Colors/Variables - Red Primary Only */
            :root {{
                --bg-color: #121212;
                --card-bg: #1f1f1f;
                --primary-action: #ef4444; /* Vivid Red for CTAs */
                --danger-color: #ef4444;
            }}
            
            body {{ 
                font-family: 'Inter', sans-serif; 
                background-color: var(--bg-color); 
            }}
            
            /* Cohesive Red Button Styling */
            .btn-primary {{
                background-color: var(--primary-action);
                color: #ffffff;
            }}
            .btn-primary:hover {{
                background-color: #dc2626; /* Slightly darker red on hover */
            }}

            /* Scrolling Marquee CSS */
            .marquee-container {{
                overflow: hidden;
                white-space: nowrap;
                width: 100%;
                margin-bottom: 1rem;
                border-bottom: 2px solid #2d2d2d;
                padding-bottom: 0.5rem;
            }}
            .marquee-text {{
                display: inline-block;
                padding-left: 100%;
                animation: marquee 20s linear infinite;
                font-size: 1.5rem;
                font-weight: 700;
                color: #374151; /* Subtle Dark gray */
            }}
            @keyframes marquee {{
                0%   {{ transform: translate(0, 0); }}
                100% {{ transform: translate(-100%, 0); }}
            }}
        </style>
    </head>
    <body class="min-h-screen flex items-center justify-center p-4">
        <div class="max-w-xl w-full bg-[var(--card-bg)] text-white p-8 md:p-10 rounded-xl shadow-2xl border-t-8 border-[var(--danger-color)] space-y-8">
            
            <!-- Scrolling Marquee Branding -->
            <div class="marquee-container">
                <div class="marquee-text">GUYSNEXTDOOR | GUYSNEXTDOOR | GUYSNEXTDOOR |</div>
            </div>

            <!-- Header & Status -->
            <div class="text-center space-y-3">
                <h1 class="text-4xl font-extrabold text-[var(--danger-color)] tracking-tight">
                    GND MANAGER
                </h1>
                <p class="text-xl text-gray-300">
                    The official home of your 24/7 administrative utility.
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
                   class="inline-block w-full sm:w-auto px-8 py-3 text-lg font-bold rounded-lg transition duration-300 btn-primary shadow-xl hover:shadow-[var(--primary-action)]/50">
                    Join the Neighborhood Discord 🏠
                </a>
            </div>
            
            <hr class="border-gray-700">

            <!-- Core Administrative Features -->
            <div class="space-y-4">
                <h2 class="text-2xl font-semibold text-gray-200">🛡️ Core Administrative Focus</h2>
                <ul class="space-y-3 text-gray-400">
                    <li class="flex items-start">
                        <span class="text-[var(--danger-color)] mr-2 mt-0.5">📜</span>
                        <p><strong>Total Accountability:</strong> All disciplinary actions are logged to the **Permanent Record** for audit and security purposes.</p>
                    </li>
                    <li class="flex items-start">
                        <span class="text-[var(--danger-color)] mr-2 mt-0.5">🔨</span>
                        <p><strong>Auto-Eviction Enforcement:</strong> Instantly re-bans any user attempting to evade a prior permanent ban.</p>
                    </li>
                </ul>
            </div>
            
            <hr class="border-gray-700">
            
            <!-- Cross-Links -->
            <div class="space-y-4">
                <h2 class="text-2xl font-semibold text-gray-200">🔗 Community Platforms</h2>
                <ul class="space-y-3 text-gray-400">
                    {
                        ''.join([
                            f"""
                            <li class="flex justify-between items-center bg-gray-700/30 p-3 rounded-lg">
                                <span class="font-medium text-white">{link['name']}</span>
                                <a href="{link['url']}" target="_blank" class="text-[var(--danger-color)] hover:underline">
                                    Visit Site &rarr;
                                </a>
                            </li>
                            """ for link in GND_LINKS
                        ])
                    }
                </ul>
            </div>


            <hr class="border-gray-700">

            <!-- Legal and Important Notice -->
            <div class="text-center text-sm text-gray-500 space-y-2">
                <p class="text-red-400 font-bold">⚠️ AGE RESTRICTION: ALL GND PLATFORMS ARE STRICTLY 18+</p>
                <p>
                    <a href="https://guysnextdoor.netlify.app/legal/policy" target="_blank" class="hover:text-[var(--danger-color)] transition">Privacy Policy</a> | 
                    <a href="https://guysnextdoor.netlify.app/legal/tos" target="_blank" class="hover:text-[var(--danger-color)] transition">Terms of Service</a>
                </p>
                <!-- Admin link is discreetly placed for staff access -->
                <p>Staff: <a href="/admin" class="hover:text-[var(--danger-color)] transition text-gray-600 font-medium border-b border-dotted border-gray-600">Admin Portal Login</a></p>
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