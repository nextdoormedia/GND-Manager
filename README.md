# 🏡 Housemate Ryker: The GuysNextDoor Community Manager

**Housemate Ryker** is a custom-built Discord bot designed exclusively for the GuysNextDoor community. Its primary function is to establish a **self-sustaining community ecosystem** that automates moderation, drives member engagement through gamification, and provides a stable, on-brand environment. By handling these operational tasks automatically, you, as the creator, can minimize management time and focus entirely on content creation and personal goals.

This bot is engineered for guaranteed 24/7 uptime using a **Web Service** hosting model (via Render/Gunicorn). This deployment method prevents the unpredictable "sleeping bot" and connection drop issues common on basic free hosting platforms, ensuring Ryker is always home and ready to manage the neighborhood.

---

## ✨ Core Features & The Vibe Economy Ecosystem

Ryker is built around the philosophy of low-maintenance, high-engagement community management. The features work together to gamify activity and protect the brand without requiring constant admin intervention.

| Feature | Description | On-Brand Terminology |
| :--- | :--- | :--- |
| **Vibe Raffle System** | All Vibe spent in the shop is pooled into a jackpot ('Free Parking') that is randomly drawn using purchased raffle tickets, keeping Vibe in the economy. | `The Vibe Free Parking Jackpot` |
| **Verification System** | Automatically grants the **Member** role to users who successfully react to the designated rules message, controlling initial server access and preventing bot spam. Includes the **!verify** redundancy command. | `New Neighbor Welcome` |
| **Vibe (XP) System** | Rewards users for sending messages with a random small amount of Vibe points (1-3 Vibe points). Includes a **15-second cooldown** to prevent channel spamming and ensure fair distribution of rewards. | `Moving Up The Block` |
| **Automatic Leveling** | Assigns and removes cosmetic rank roles when a member reaches a new Vibe milestone. Nicknames are also updated with purchased **Icons (Prefix)** and **Flairs (Suffix)**. | `Neighborhood Ranks & Flairs` |
| **Vibe Economy** | Allows users to spend earned Vibe on custom cosmetics and specialized access via the `!shop` command. | `Vibe Shop` |
| **Prestige System** | Rewards highly active members who reach the Vibe cap (`Block Captain`) by resetting their Vibe to zero and granting a permanent `Legacy Resident` tier. | `Graduating to Legacy` |
| **Disciplinary Alerts** | Automatically logs all membership changes (leaves/bans) and administrative Vibe deductions to the Mod Alerts Channel for full oversight. | `Neighborhood Watch Logs` |
| **Data Integrity** | Bot data is saved every 5 minutes and after every transaction, ensuring user progress is protected against reboots or crashes. | `Always Saving Progress` |
| **Confidential Reporting** | Allows users to privately and anonymously report rule-breakers directly to the **Mod Alerts Channel** via DM using the `!report` command, protecting the reporter's identity. | `House Safety Report` |
| **Content Filters** | Automatically deletes messages containing known promotional links, specific spam keywords, or explicitly forbidden content, while alerting the user. | `Keeping the Neighborhood Clean` |
| **Uptime Management** | Runs a Flask web server in a background thread to satisfy the hosting service's health checks, guaranteeing continuous 24/7 uptime. | `Always Home` |

---

## 📋 Full Command Reference

| Command | Category | Description |
| :--- | :--- | :--- |
| **`!profile`** | **Economy** | Displays your current Vibe score, Rank, Daily Streak, Legacy Tier, and Nickname Cosmetics. |
| **`!daily`** | **Economy** | Claim your daily Vibe reward and increase your streak bonus. |
| **`!rank`** | **Economy** | Shows your current rank tier and Vibe required for the next rank. |
| **`!leaderboard`** | **Economy** | Displays the top 10 Vibe earners in the neighborhood. |
| **`!shop`** | **Economy** | Lists all items available for purchase with Vibe. |
| **`!buy [ID]`** | **Economy** | Purchases an item from the Vibe Shop. Vibe spent is added to the Raffle Pool. |
| **`!gift [member] 50`** | **Economy** | Purchases and instantly sends 50 Vibe to another member at a cost of 300 Vibe. |
| **`!prestige`** | **Economy** | Resets your Vibe score to 0 to earn the next permanent Legacy Resident Tier. |
| **`!report [member] [reason]`** | **Community** | Confidential report command; sends an anonymous alert to the Mod Alerts Channel. |
| **`!verify`** | **Utility** | **Redundancy command** to grant the Member role if the reaction fails. |
| **Admin `!raffle_draw`** | **Administration** | **CRITICAL:** Draws the winner from the Vibe Pool, distributes the prize, and handles rollover logic. |
| **Admin `!deduct_vibe [member] [amount] [reason]`**| **Administration** | Deducts Vibe from a user for disciplinary reasons and logs the action to Mod Alerts. |
| **Admin `!set_vibe [member] [amount]`** | **Administration** | Manually sets a member's Vibe score and forces a rank update. |
| **Admin `!set_icon [member] [emoji]`** | **Administration** | Sets a short emoji icon (prefix) for a member's nickname. |
| **Admin `!set_flair [member] [text]`** | **Administration** | Sets a short text flair (suffix) for a member's nickname. |
| **Admin `!clear_flair [member]`** | **Administration** | Removes the custom text flair from a member's nickname. |
| **Admin `!update_ranks [member]`** | **Administration** | Force re-checks and re-applies all rank roles and nickname cosmetics for a member. |
| **Admin `!say [channel] [message]`** | **Administration** | Posts a message as the bot to a specified channel. |

---

## 🛠️ Critical Configuration & Setup (The Control Panel)

For Ryker to function correctly, the **Control Panel** in the code and the **Discord roles** must be synchronized perfectly. **Incorrect configuration of IDs or Role Names will cause the bot to fail silently.**

### 1. Bot Configuration: The Top of the Script

The operational settings are contained in simple variables at the very top of the `housemate_ryker.py` file. This top section is your primary non-technical interface for managing the bot's behavior.

* **CRUCIAL IDs:** You must manually update all **CHANNEL IDs** (e.g., Mod Alerts) and the **VERIFICATION MESSAGE ID** by copying them directly from Discord's developer mode. Ryker uses these IDs to know exactly where to watch for reactions, send reports, and post moderator alerts.
* **Raffle Control:** New constants (`MIN_RAFFLE_POOL`, `MAX_RAFFLE_POOL`) control the jackpot size and ensure the raffle only draws when the prize is meaningful.
* **Data Persistence:** The bot automatically saves all user Vibe, Streak, and Cosmetic data, as well as the **Raffle Pool data** (under the `GLOBAL_RAFFLE_DATA` key) into a single file called `vibe_data.json`. This centralized **JSON database** is essential for persistence.

### 2. Discord Role Setup (Must Match Exactly!)

The bot manages the assignment and removal of roles. Therefore, the roles **must** be created in your Discord server first, and the bot's role must be positioned correctly.

* **Hierarchy Requirement:** The bot's own role must be placed **higher** in the Discord role hierarchy than *any* of the ranks it is expected to manage (including the base `Member` role). If the bot's role is too low, it will lack the permission to grant ranks.
* **Role Names:** The names must match the configuration variables exactly, down to capitalization and spelling.

| Role Type | Role Name (Must Match Exactly!) | Purpose and Persistence |
| :--- | :--- | :--- |
| **Access Role** | `Member` | The base role granted by the verification system. The gateway to the server. |
| **Basic Ranks** | `New Neighbor`, `Familiar Face`, `Resident`, `Housemate`, `Block Captain` | **Tiered & Temporary.** These are automatically *assigned and removed* as a user's Vibe total fluctuates up or down. |
| **End-Game Ranks** | `Legacy Resident I`, `Legacy Resident II`, `Legacy Resident III`, etc. | **Permanent.** These are granted upon using the `!prestige` command and are never removed. They symbolize permanent loyalty to the community. |

### 3. Hosting Security & Uptime Architecture

Ryker uses a specific deployment architecture to guarantee continuous uptime on hosting services that use a health-check system (like Render's Web Service).

* **The "Heartbeat" Strategy:** The bot runs using a "Web Service" structure where the main process (`gunicorn`) runs a simple Flask web server. This web server serves only one function: it responds to the hosting service's mandatory external **health checks** via the `/` endpoint.
* **Multithreading:** The actual Discord bot client, which is a blocking process, runs in a **separate background thread** created by the Flask application. This prevents the Discord connection from freezing the main web server process, ensuring that when the host checks if the bot is "awake," the answer is always yes.

---

## 🧪 Housemate Ryker: Simplified Manual Testing Guide

Use this comprehensive table to quickly verify that all core features, filters, and command behaviors are operating correctly in your server.

| Feature to Test | Step 1: Action (Type This Command or Message) | Step 2: Expected Result (What You Should See) |
| :--- | :--- | :--- |
| **Verification System** | React to the Rules message (ID set in config) with the **✅** emoji. | You are instantly granted the **Member** role and gain visibility to the general channels. The bot should not post any public message. |
| **Core Vibe Earning** | Send one message. Wait **15 seconds**. Send a second message. | Both messages stay. **Crucial Check:** You should only get Vibe from the **second message**, confirming the cooldown logic is correctly preventing spam rewards. |
| **Daily Streak** | Type: `!daily` | **(1)** A successful embed appears confirming Vibe added, and the streak counter increases. **(2)** Run `!daily` immediately again: bot sends an error about the time/date, confirming the 24-hour reset is enforced. |
| **Admin Setup: Give Vibe** | `!set_vibe @YourUsername 5000` | **(1)** Bot replies: *Set Vibe for...* **(2)** Your cosmetic rank automatically updates to the highest basic rank (`Block Captain`). |
| **Admin Setup: Deduct Vibe** | `!deduct_vibe @YourUsername 100 Testing disciplinary alert.` | **(1)** Bot replies: *Deducted 100 Vibe...* **(2) Crucial Check:** A red **Vibe Deduction Alert** embed appears in the Mod Alerts Channel, logging the action and moderator. |
| **Admin Setup: Nickname Flair** | `!set_flair @YourUsername 🏠` then `!set_flair @YourUsername [Text]` | **(1)** Nickname updates to show `🏠` as a prefix. **(2)** Nickname updates to show `[Text]` as a suffix. **(3)** Use `!clear_flair` to remove the suffix. |
| **Prestige Command** | Ensure Vibe is over the cap (e.g., 2000). Type: `!prestige` | **(1)** Bot confirms reset, setting Vibe to `0`. **(2)** The bot grants the permanent `Legacy Resident I` role. Run `!profile` to verify Vibe is 0 but the Legacy role is present. |
| **Confidential Report** | In a **DM with the bot**, type: `!report @NeighborName Test Reason` | The bot sends a confirmation to your DMs, and a **User Report** embed appears in the **Mod Alerts Channel**. **Check:** Your username should *not* be in the Mod Alerts embed (confirming anonymity). |
| **Purchase Log** | Type: `!buy 5` (A manual fulfillment item). | **(1)** Bot replies: *Purchase Complete...* **(2) Crucial Check:** A yellow/red alert embed appears in the **Mod Alerts Channel** detailing the purchase AND confirming the cost was added to the Raffle Pool. |
| **Raffle Pool & Draw** | **Setup:** Have at least one person buy `!buy 11`. **Action:** `!raffle_draw` | **(1)** Bot announces the winner in the designated channel. **(2)** Winner's Vibe is increased by the jackpot amount. **(3)** The Raffle Pool resets, retaining any rollover amount. |
| **Spam Link Filter** | Send a message containing a suspicious link: `Check this out: bit.ly/spamurl` | **(1) Your message is immediately deleted.** **(2)** The bot briefly posts a temporary **removal notice** in the channel and notifies the user via DM (if DM is open). |
| **Admin Announcement** | `!say #general **This is an announcement.**` | Your command message is **deleted**, and the bot posts the bolded message to the `#general` channel, validating your moderator authority. |

### 🛑 Troubleshooting Quick-Check

| Problem | Likely Cause | Fix |
| :--- | :--- | :--- |
| **Bot won't start/Offline.** | The `DISCORD_TOKEN` environment variable is missing or wrong. | Re-enter the token in your hosting service's environment variables. |
| **Bot can't grant roles/ranks.** | The bot's role in Discord is lower than the ranks it manages. | Drag the bot's role to the highest position (just below Administrator/Owner roles). |
| **Vibe earning is slow/non-existent.** | The 15-second cooldown is not being respected. | Wait the full 15 seconds between test messages. Check the `COOLDOWN_SECONDS` variable in the script. |
| **Filters don't delete messages.**| The bot is missing the `Message Content` intent. | Check the application settings on the Discord Developer Portal to ensure the `Message Content` intent is explicitly enabled. |