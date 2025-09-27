# 🏡 GND Manager: The GuysNextDoor Community Utility

**GND Manager** is a custom-built Discord bot designed exclusively for the GuysNextDoor community. Its primary function is to serve as a reliable, **always-on administrative utility**, automating essential tasks to ensure a stable, safe, and organized environment.

This bot is engineered for guaranteed **24/7 uptime** using a **Web Service** hosting model (via Flask/Gunicorn). This deployment method prevents the unpredictable "sleeping bot" and connection drop issues common on basic free hosting platforms, ensuring the Manager is always available to run the neighborhood.

* * *

## ✨ Core Features: Administration & Security

The Manager is built around the philosophy of **high security and total accountability**, with a core focus on logging and auto-enforcement.

| Feature | Description | On-Brand Terminology |
| --- | --- | --- |
| **Disciplinary Logging** | **MANDATORY**: All disciplinary actions (`Kick`, `Ban`, `Mute`, `Report`) are permanently logged to a local JSON file (`mod_logs.json`) for audit purposes. | `Permanent Record` |
| **Ban Evasion Prevention** | Automatically checks the permanent log upon a member joining. If a prior **BAN** action is found, the user is instantly re-banned. | `Auto-Eviction Enforcement` |
| **User Lookup** | Command (`!whois @User`) retrieves a user's account details, roles, and displays a summary of their logged disciplinary history. | `Background Check` |
| **Mute/Unmute** | Admin commands (`!mute`, `!unmute`) apply or remove the designated Muted role for temporary suspensions. | `Temporary Suspension` |
| **Verification System** | Automatically grants the **Member** role to users who successfully react to the designated rules message, controlling initial access. | `New Neighbor Welcome` |
| **Content Filters** | Automatically deletes and notifies users who post spam links or promotional content outside of designated areas. | `Neighborhood Watch` |
| **User Reporting** | Allows any user to discreetly submit a report about another member directly to the moderator alert channel. **The report is also logged.** | `Tattletale Tool` |
| **Mass Purge** | Admin command (`!purge`) to quickly delete a specified number of recent messages from a channel. | `Clean-Up Duty` |
| **Kick/Ban** | The final disciplinary tools (`!kick`, `!ban`). **Actions are logged and drive the auto-enforcement system.** | `Eviction Notice` |

* * *

## 🔧 Core Features: User Utilities & Information

These new commands give members easy access to server information, schedules, and management data.

| Command | Description | On-Brand Terminology |
| --- | --- | --- |
| **`!status`** | Displays the **GND Manager**'s current uptime and system latency (ping). | `Premises Report` |
| **`!rules`** | Posts an abbreviated, easy-to-read summary of the essential server rules. | `The Lease Agreement` |
| **`!schedule`** | Displays the official weekly schedule for all content drops, streams, and community events. | `Weekly Rota` |
| **`!links`** | Provides a list of all official content platforms and support links (Chaturbate, PornHub, Website, etc.). | `The Keyring` |
| **`!invite`** | Generates a permanent invite link to share the community with friends. | `The Key` |
| **`!serverstats`** | Displays key administrative data on the community's activity, growth, and health. _(Awaiting full data integration)_ | `The Ledger` |

* * *

## 🛠️ Deployment and Files

| File | Purpose | Key Details |
| --- | --- | --- |
| **`app.py`** | **Deployment Entrypoint & Web Server** | Sets up the **Flask** web server and starts the Discord bot in a background thread, ensuring stable 24/7 operation. |
| **`bot_logic.py`** | **Bot Logic, Commands, & Configuration** | Contains all the Discord bot's event listeners, moderation filters, and the new **Admin and User Utility Commands**. |
| **`mod_logs.json`** | **Permanent Moderation Database** | The local JSON file used to store the history of all disciplinary actions for lookup and auto-enforcement. |
| **`Procfile`** | **Hosting Command** | Single line: `web: gunicorn app:app`. Instructs the hosting platform (e.g., Render) to run the Flask application via Gunicorn. |
| **`requirements.txt`** | **Dependencies** | Lists required Python packages: `discord.py`, `Flask`, and `gunicorn`. |

* * *

## ⚙️ Testing and Admin Commands

The bot uses the prefix `!` for all commands.

| Feature | Test Command | Expected Result |
| --- | --- | --- |
| **User Lookup** | `!whois @User` | Bot returns an embed showing the user's details and their last few disciplinary actions. |
| **Mute/Unmute** | `!mute @User Excessive Noise` | User receives the `Muted` role, and the action is logged. `!unmute @User`reverses this. |
| **Report Log** | `!report @User Being rude` | The user who executes the command receives a success DM, and the action is **logged to the database** and sent to the mod alert channel. |
| **New Status Check** | `!status` | Bot returns an embed showing the current **Uptime** and **Latency (Ping)**. |
| **New Utility** | `!schedule` | Bot returns an embed showing all content drops and community event times. |
| **Admin Announcement** | `!say #general **This is an announcement.**` | Your command message is **deleted**, and the bot posts the bolded message to the `#general` channel. |
