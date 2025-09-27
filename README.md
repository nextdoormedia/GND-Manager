# 🏡 Housemate Ryker: The GuysNextDoor Community Manager

**Housemate Ryker** is a custom-built Discord bot designed exclusively for the GuysNextDoor community. Its primary function is to serve as a reliable, **always-on moderator and administrator utility**, automating essential tasks to ensure a stable, safe, and clean environment.

This bot is engineered for guaranteed **24/7 uptime** using a **Web Service** hosting model (via Flask/Gunicorn). This deployment method prevents the unpredictable "sleeping bot" and connection drop issues common on basic free hosting platforms, ensuring Ryker is always home and ready to manage the neighborhood.

* * *

## ✨ Core Features: Administration & Security (Updated)

Ryker is built around the philosophy of **high security and low-maintenance** community management, with a core focus on **accountability through logging and auto-enforcement**.

| Feature | Description | On-Brand Terminology |
| --- | --- | --- |
| **Disciplinary Logging** | **MANDATORY**: All disciplinary actions (`Kick`, `Ban`, `Mute`, `Report`) are permanently logged to a local JSON file (`mod_logs.json`) for accountability and audit purposes. | `Permanent Record` |
| **Ban Evasion Prevention** | Automatically checks the permanent log upon a member joining. If a prior **BAN** action is found, the user is instantly re-banned, enforcing permanent evictions. | `Auto-Eviction Enforcement` |
| **User Lookup** | Command (`!whois @User`) retrieves a user's account details, roles, and displays a summary of their logged disciplinary history. | `Background Check` |
| **Mute/Unmute** | Admin commands (`!mute`, `!unmute`) apply or remove the designated Muted role for temporary suspensions. All actions are logged. | `Temporary Suspension` |
| **Verification System** | Automatically grants the **Member** role to users who successfully react to the designated rules message, controlling initial access. Also available via the `!verify` command. | `New Neighbor Welcome` |
| **Content Filters** | Automatically deletes and notifies users who post spam links, prohibited keywords, or promotional content. | `Neighborhood Watch` |
| **User Reporting** | Allows any user to discreetly submit a report about another member or issue directly to the moderator alert channel. **The report action is also logged.** | `Tattletale Tool` |
| **Mass Purge** | Admin command (`!purge`) to quickly delete a specified number of recent messages from a channel. | `Clean-Up Duty` |
| **Kick/Ban** | The final disciplinary tools (`!kick`, `!ban`). **Actions are logged and drive the auto-enforcement system.** | `Eviction Notice` |

* * *

## 🛠️ Deployment and Files (Updated)

| File | Purpose | Key Details |
| --- | --- | --- |
| **`app.py`** | **Deployment Entrypoint & Web Server** | Sets up the **Flask** web server (for the host's health check) and starts the Discord bot in a background thread, ensuring concurrent and stable 24/7 operation. |
| **`bot_logic.py`** | **Bot Logic, Commands, & Configuration** | Contains all the Discord bot's event listeners, moderation filters, commands, and configuration variables (the **Control Panel**). |
| **`mod_logs.json`** | **Permanent Moderation Database** | The local JSON file used to store the history of all disciplinary actions (Kick, Ban, Mute, Report) for lookup and auto-enforcement. |
| **`Procfile`** | **Hosting Command** | Single line: `web: gunicorn app:app`. Instructs the hosting platform (e.g., Render) to run the Flask application via Gunicorn. |
| **`requirements.txt`** | **Dependencies** | Lists required Python packages: `discord.py`, `Flask`, and `gunicorn`. |

* * *

## ⚙️ Testing and Admin Commands (Updated)

The bot uses the prefix `!` for all commands.

| Feature | Test Command | Expected Result |
| --- | --- | --- |
| **User Lookup** | `!whois @User` | Bot returns an embed showing the user's details and their last few disciplinary actions from the `mod_logs.json` database. |
| **Mute/Unmute** | `!mute @User Excessive Noise` | User receives the `Muted` role, and the action is logged to `mod_logs.json`. `!unmute @User` reverses this. |
| **Report Log** | `!report @User Being rude` | The user who executes the command receives a success DM, and the action is **logged to the database** and sent to the mod alert channel. |
| **Ban & Enforcement** | `!ban @User Evasion Threat` | User is banned, the action is **logged**. If the user attempts to rejoin, the bot automatically re-bans them upon entry. |
| **Mass Purge** | `!purge 5` | Bot deletes the 5 messages preceding the command and posts a temporary success notice. |
| **Admin Kick** | `!kick @User Spamming in chat` | The user is removed from the server, and the action is **logged** to `mod_logs.json`. |
| **Spam Link Filter** | Send a message containing a suspicious link: `Check this out: bit.ly/spamurl` | **(1) Your message is immediately deleted.** **(2)** The bot posts a temporary **removal notice** in the channel. |
| **Admin Announcement** | `!say #general **This is an announcement.**` | Your command message is **deleted**, and the bot posts the bolded message to the `#general` channel. |