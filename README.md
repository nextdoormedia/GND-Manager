# 🏡 Housemate Ryker: The GuysNextDoor Community Manager

**Housemate Ryker** is a custom-built Discord bot designed exclusively for the GuysNextDoor community. Its primary function is to serve as a reliable, **always-on moderator and administrator utility**, automating essential tasks to ensure a stable, safe, and clean environment.

This bot is engineered for guaranteed **24/7 uptime** using a **Web Service** hosting model (via Flask/Gunicorn). This deployment method prevents the unpredictable "sleeping bot" and connection drop issues common on basic free hosting platforms, ensuring Ryker is always home and ready to manage the neighborhood.

---

## ✨ Core Features: Administration & Security

Ryker is built around the philosophy of **high security and low-maintenance** community management.

| Feature | Description | On-Brand Terminology |
| :--- | :--- | :--- |
| **Verification System** | Automatically grants the **Member** role to users who successfully react to the designated rules message, controlling initial server access and preventing bot spam. | `New Neighbor Welcome` |
| **Content Filters** | Automatically deletes and notifies users who post spam links, prohibited keywords, or promotional content. | `Neighborhood Watch` |
| **User Reporting** | Allows any user to discreetly submit a report about another member or issue directly to the moderator alert channel. | `Tattletale Tool` |
| **Admin Announcement** | Provides a command (`!say`) for administrators to securely post a clean message to any channel via the bot. | `Ryker's Bulletin` |
| **Mass Purge** | Admin command (`!purge`) to quickly delete a specified number of recent messages from a channel to clear spam or off-topic content. | `Clean-Up Duty` |
| **Kick/Ban** | The final disciplinary tools (`!kick`, `!ban`) for removing persistent problem users. | `Eviction Notice` |

---

## 🛠️ Deployment and Files

| File | Purpose | Key Details |
| :--- | :--- | :--- |
| **`app.py`** | **Deployment Entrypoint & Web Server** | Sets up the **Flask** web server (for the host's health check) and starts the Discord bot in a background thread, ensuring concurrent and stable 24/7 operation. |
| **`bot_logic.py`** | **Bot Logic, Commands, & Configuration** | Contains all the Discord bot's event listeners, moderation filters, commands, and configuration variables (the **Control Panel**). |
| **`Procfile`** | **Hosting Command** | Single line: `web: gunicorn app:app`. Instructs the hosting platform (e.g., Render) to run the Flask application via Gunicorn. |
| **`requirements.txt`** | **Dependencies** | Lists required Python packages: `discord.py`, `Flask`, and `gunicorn`. |

---

## ⚙️ Testing and Admin Commands

The bot uses the prefix `!` for all commands.

| Feature | Test Command | Expected Result |
| :--- | :--- | :--- |
| **Mass Purge** | `!purge 5` | Bot deletes the 5 messages preceding the command and posts a temporary success notice. |
| **Admin Kick** | `!kick @User Spamming in chat` | The user is removed from the server, and a confirmation appears in the channel. |
| **Spam Link Filter** | Send a message containing a suspicious link: `Check this out: bit.ly/spamurl` | **(1) Your message is immediately deleted.** **(2)** The bot posts a temporary **removal notice** in the channel. |
| **Admin Announcement** | `!say #general **This is an announcement.**` | Your command message is **deleted**, and the bot posts the bolded message to the `#general` channel. |
```eof
