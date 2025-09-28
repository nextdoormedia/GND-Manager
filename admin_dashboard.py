import os
import json
import time
from flask import Blueprint, render_template_string, request
from flask_httpauth import HTTPBasicAuth
from datetime import datetime, timedelta

# Import necessary components and constants from the bot logic module
from .bot_logic import MOD_LOGS_FILE, METRICS_FILE, bot, BOT_START_TIME, ACTIVE_CHATTERS 

# --- FLASK BLUEPRINT & AUTHENTICATION SETUP ---

admin_bp = Blueprint('admin', __name__)
auth = HTTPBasicAuth()

# Credentials sourced from environment variables for security
ADMIN_USER = os.getenv('ADMIN_USER')
ADMIN_PASS = os.getenv('ADMIN_PASS')

# --- DATA ACCESS & PROCESSING HELPERS ---

def load_json(filepath):
    """Safely loads JSON data from a file on disk."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
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


def calculate_metrics(metrics_data):
    """Processes raw server_metrics data into actionable insights (Phase 3 & 4)."""
    
    # 1. Churn and Retention Calculation (Last 7 Days)
    today = datetime.now().date()
    
    join_log = {datetime.fromisoformat(k).date(): v for k, v in metrics_data.get('join_log', {}).items()}
    leave_log = {datetime.fromisoformat(k).date(): v for k, v in metrics_data.get('leave_log', {}).items()}
    
    recent_joins = 0
    recent_leaves = 0
    
    # Aggregate data for the last 7 days
    for i in range(7):
        date = today - timedelta(days=i)
        recent_joins += join_log.get(date, 0)
        recent_leaves += leave_log.get(date, 0)
        
    net_change = recent_joins - recent_leaves
    
    if recent_joins > 0:
        churn_rate = (recent_leaves / recent_joins) * 100
        retention_rate = 100 - churn_rate
    else:
        churn_rate = 0
        retention_rate = 0 
        
    # 2. Channel Activity (Top 5)
    raw_activity = metrics_data.get('channel_activity_log', {})
    
    # Sort channel activity by message count (value)
    sorted_activity = sorted(
        [(int(cid), count) for cid, count in raw_activity.items()],
        key=lambda item: item[1],
        reverse=True
    )
    
    top_channels = []
    total_messages = sum(count for cid, count in sorted_activity)
    
    for channel_id, count in sorted_activity[:5]:
        channel = bot.get_channel(channel_id)
        # Use a fallback name if the bot cannot resolve the channel ID (e.g., if it was deleted)
        name = f"#{channel.name}" if channel else f"#{channel_id}"
        percentage = (count / total_messages) * 100 if total_messages > 0 else 0
        
        top_channels.append({
            'name': name,
            'count': count,
            'percent': f"{percentage:.1f}%"
        })

    # 3. Monthly Summary (Moderation Actions)
    summary = metrics_data.get('monthly_summary', {})

    return {
        'retention_rate': f"{retention_rate:.1f}%",
        'net_change': net_change,
        'recent_joins': recent_joins,
        'monthly_bans': summary.get('total_bans', 0),
        'monthly_mutes': summary.get('total_mutes', 0),
        'monthly_kicks': summary.get('total_kicks', 0),
        'top_channels': top_channels
    }

# --- AUTHENTICATION LOGIC ---

@auth.verify_password
def verify_password(username, password):
    """Verifies the username and password against the environment variables."""
    if not ADMIN_USER or not ADMIN_PASS:
        # Fails closed if credentials aren't set
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
    
    # 1. Load Data
    mod_logs_data = load_json(MOD_LOGS_FILE)
    metrics_data = load_json(METRICS_FILE)
    
    # 2. Process Metrics
    processed_metrics = calculate_metrics(metrics_data)
    total_logs = len(mod_logs_data.get('logs', []))

    # 3. Uptime/Health Data
    uptime_seconds = int(time.time() - BOT_START_TIME)
    uptime_display = str(timedelta(seconds=uptime_seconds)).split('.')[0] 
    latency_ms = round(bot.latency * 1000) if bot.is_ready() else "N/A"
    
    # 4. Search Functionality
    search_results = None
    search_id = request.form.get('target_id')
    
    if request.method == 'POST' and search_id:
        user_logs = [log for log in mod_logs_data.get('logs', []) if log.get('target_id') == search_id]
        search_results = user_logs
        
    # 5. Log Summary (Last 10 actions)
    log_summary = mod_logs_data.get('logs', [])[:10]
    
    # 6. Command Documentation
    command_docs = get_bot_commands_doc()
    
    # --- HTML & STYLING ---
    
    # Define color mappings for the dashboard tiles
    status_color = '#2ecc71' if bot.is_ready() and latency_ms != 'N/A' and latency_ms < 500 else '#f1c40f'
    status_text = 'ONLINE' if status_color == '#2ecc71' else 'DEGRADED / STARTING'
    
    # Helper to convert log entries to HTML list items
    def format_log(log):
        dt_obj = datetime.fromisoformat(log['timestamp'].split('.')[0])
        time_str = dt_obj.strftime('%Y-%m-%d %H:%M')
        
        # Use action to determine color/icon
        action_color = {
            'BAN': 'bg-red-500', 
            'KICK': 'bg-orange-500', 
            'MUTE': 'bg-gray-500',
            'REPORT': 'bg-blue-500'
        }.get(log['action'], 'bg-indigo-500')
        
        return f"""
        <li class="p-3 border-b border-gray-100 flex justify-between items-start text-sm">
            <div>
                <span class="font-bold {action_color} text-white px-2 py-0.5 rounded-full text-xs">
                    {log['action']}
                </span>
                <span class="text-gray-600 ml-2">ID: {log['target_id']}</span>
                <p class="text-xs mt-1 text-gray-500 truncate" title="{log['reason']}">Reason: {log['reason']}</p>
            </div>
            <div class="text-right text-xs text-gray-400">
                {time_str}
            </div>
        </li>
        """

    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GND Manager Admin Dashboard</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@100..900&display=swap');
            body {{ font-family: 'Inter', sans-serif; background: #f8fafc; }}
            .sidebar {{ background: #ffffff; border-right: 1px solid #e2e8f0; }}
            .metric-value {{ font-size: 2.25rem; font-weight: 700; }}
            .metric-label {{ text-transform: uppercase; font-size: 0.75rem; color: #64748b; }}
            .search-input {{ transition: border-color 0.2s; }}
            .search-input:focus {{ border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.5); }}
        </style>
    </head>
    <body class="min-h-screen">
        <div class="bg-gray-900 text-white shadow-lg p-4 sticky top-0 z-10">
            <h1 class="text-2xl font-bold tracking-tight">
                <span class="text-red-500">🛡️</span> GND Manager Command Center
            </h1>
        </div>
        
        <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 grid lg:grid-cols-4 gap-8">
            
            <!-- Left Column: Metrics and Health (lg:col-span-1) -->
            <div class="lg:col-span-1 space-y-8">
                
                <!-- Bot Health Card -->
                <div class="bg-white p-6 rounded-xl shadow-md border-t-4" style="border-top-color: {status_color};">
                    <h2 class="text-xl font-semibold mb-4 text-gray-800 flex justify-between items-center">
                        Bot Health
                        <span class="text-xs font-medium px-3 py-1 rounded-full text-white" style="background-color: {status_color};">
                            {status_text}
                        </span>
                    </h2>
                    <div class="space-y-2 text-sm">
                        <p class="flex justify-between"><strong>Latency:</strong> <span>{latency_ms} ms</span></p>
                        <p class="flex justify-between"><strong>Uptime:</strong> <span>{uptime_display}</span></p>
                        <p class="flex justify-between"><strong>Total Logs:</strong> <span>{total_logs}</span></p>
                    </div>
                </div>

                <!-- Moderation Metrics -->
                <div class="bg-white p-6 rounded-xl shadow-md">
                    <h2 class="text-xl font-semibold mb-4 text-gray-800">Monthly Moderation</h2>
                    <div class="space-y-3">
                        <div class="flex justify-between items-center p-2 rounded-lg bg-red-50 border border-red-200">
                            <span class="text-red-600 font-medium">Bans Issued</span>
                            <span class="metric-value text-red-700 text-lg">{processed_metrics['monthly_bans']}</span>
                        </div>
                        <div class="flex justify-between items-center p-2 rounded-lg bg-orange-50 border border-orange-200">
                            <span class="text-orange-600 font-medium">Kicks Issued</span>
                            <span class="metric-value text-orange-700 text-lg">{processed_metrics['monthly_kicks']}</span>
                        </div>
                        <div class="flex justify-between items-center p-2 rounded-lg bg-gray-50 border border-gray-200">
                            <span class="text-gray-600 font-medium">Mutes Issued</span>
                            <span class="metric-value text-gray-700 text-lg">{processed_metrics['monthly_mutes']}</span>
                        </div>
                    </div>
                </div>

                <!-- Command Documentation -->
                <div class="bg-white p-6 rounded-xl shadow-md">
                    <h2 class="text-xl font-semibold mb-4 text-gray-800">Bot Command Reference</h2>
                    <div class="space-y-3">
                        {
                            ''.join([
                                f"""
                                <div class="bg-blue-50 p-3 rounded-lg border border-blue-200">
                                    <code class="font-mono text-blue-700 text-sm block">!{cmd['usage']}</code>
                                    <small class="text-gray-600 text-xs block mt-1">{cmd['description']}</small>
                                </div>
                                """
                                for cmd in command_docs
                            ])
                        }
                    </div>
                </div>
            </div>
            
            <!-- Right Column: Analytics and Logs (lg:col-span-3) -->
            <div class="lg:col-span-3 space-y-8">
                
                <!-- Retention & Activity Overview -->
                <div class="grid md:grid-cols-3 gap-6">
                    
                    <!-- Metric Card 1: Retention -->
                    <div class="bg-white p-6 rounded-xl shadow-md border-l-4 border-green-500">
                        <p class="metric-label">7-Day Retention Rate</p>
                        <p class="metric-value text-green-600">{processed_metrics['retention_rate']}</p>
                        <p class="text-sm text-gray-500">({processed_metrics['recent_joins']} joins vs {processed_metrics['recent_joins'] - processed_metrics['net_change']} leaves)</p>
                    </div>

                    <!-- Metric Card 2: Net Change -->
                    <div class="bg-white p-6 rounded-xl shadow-md border-l-4 border-indigo-500">
                        <p class="metric-label">Net Member Change (7D)</p>
                        <p class="metric-value { 'text-green-600' if processed_metrics['net_change'] >= 0 else 'text-red-600' }">
                            {'+' if processed_metrics['net_change'] >= 0 else ''}{processed_metrics['net_change']}
                        </p>
                        <p class="text-sm text-gray-500">Measure of community health.</p>
                    </div>

                    <!-- Metric Card 3: Active Chatters -->
                    <div class="bg-white p-6 rounded-xl shadow-md border-l-4 border-yellow-500">
                        <p class="metric-label">Unique Active Chatters (In-Memory)</p>
                        <p class="metric-value text-yellow-600">{len(ACTIVE_CHATTERS)}</p>
                        <p class="text-sm text-gray-500">Users who have sent a message since bot restart.</p>
                    </div>
                </div>
                
                <!-- Channel Activity and Log Search Container -->
                <div class="grid md:grid-cols-2 gap-6">
                    
                    <!-- Channel Activity -->
                    <div class="bg-white p-6 rounded-xl shadow-md">
                        <h2 class="text-xl font-semibold mb-4 text-gray-800">Top 5 Channel Activity</h2>
                        <ul class="divide-y divide-gray-100">
                            {
                                ''.join([
                                    f"""
                                    <li class="flex justify-between items-center py-3">
                                        <span class="text-gray-700 font-medium">{i+1}. {channel['name']}</span>
                                        <div class="text-right">
                                            <span class="text-blue-600 font-bold">{channel['percent']}</span>
                                            <span class="text-gray-400 text-sm">({channel['count']} msgs)</span>
                                        </div>
                                    </li>
                                    """
                                    for i, channel in enumerate(processed_metrics['top_channels'])
                                ]) if processed_metrics['top_channels'] else '<li class="text-gray-500 py-3">No activity logged yet.</li>'
                            }
                        </ul>
                    </div>

                    <!-- Log Search -->
                    <div class="bg-white p-6 rounded-xl shadow-md">
                        <h2 class="text-xl font-semibold mb-4 text-gray-800">Moderation Record Search</h2>
                        <form method="POST">
                            <input type="text" name="target_id" placeholder="Enter Discord User ID" required
                                class="search-input w-full p-3 mb-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                            <button type="submit" 
                                class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-4 rounded-lg transition duration-150">
                                Search Permanent Record
                            </button>
                        </form>
                    </div>
                </div>

                <!-- Search Results / Full Log List -->
                <div class="bg-white rounded-xl shadow-md overflow-hidden">
                    <h2 class="text-xl font-semibold p-6 text-gray-800 border-b">
                        {
                            f"Search Results for ID: {search_id} ({len(search_results)} Total Logs)" 
                            if search_results is not None else "Recent Moderation Log Summary (Last 10)"
                        }
                    </h2>
                    <ul class="divide-y divide-gray-200">
                        {
                            # Display search results if available, otherwise display the summary
                            ''.join(format_log(log) for log in (search_results if search_results is not None else log_summary))
                        }
                        {
                            f'<li class="p-4 text-center text-gray-500">No logs found for ID: {search_id}.</li>'
                            if search_results == [] else ''
                        }
                    </ul>
                </div>
                
            </div>
            
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_content)
