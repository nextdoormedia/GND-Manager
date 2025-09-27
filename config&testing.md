* * *
# Housemate Ryker: Companion Guide for Non-Coders 🛠️

This document serves as your complete, non-technical guide for managing, configuring, and testing *Housemate Ryker*. It is optimized for minimal setup and assumes no prior coding experience.

* * *

## 1. Detailed Instructions \& Setup (The Control Panel)

Before testing, you must ensure the server environment is correctly set up. These are the *only* management tasks required outside of the bot's Python code.

### 1.1. ⚙️ Bot Configuration: The Top of the Script

All bot settings (like Vibe amounts, channels, and forbidden words) are controlled by simple text variables at the very top of the **housemate_ryker.py** file. Think of this section as your *Bot Control Panel*.

* **Crucial:** You must ensure the **CHANNEL IDs** are correct for your server (e.g., `WELCOME_CHANNEL_ID`, `MOD_ALERTS_CHANNEL_ID`).
* **Tuning:** If you ever want to change how much Vibe users earn or the shop prices, you only need to change the numbers in this top section. *No other code changes are necessary.*

### 1.2. 👑 Discord Role Setup (Critical!)

The bot grants, removes, and manages all ranks automatically, but the roles **must** be created in your Discord server first. They must match the names exactly.

| Role Type | Role Name (Must Match Exactly!) | Purpose |
| :--- | :--- | :--- |
| **Basic Ranks** | `New Neighbor`, `Familiar Face`, `Resident`, `Housemate`, `Block Captain` | Granted automatically based on Vibe total. |
| **End-Game Ranks** | `Legacy Resident I`, `Legacy Resident II`, `Legacy Resident III` (and so on) | Permanent roles granted after a user uses `!prestige`. |

### 1.3. 🔑 Hosting Security (The Only Code-Adjacent Task)

The bot runs 24/7 on a service like Render. The only thing you need to manage for deployment is a single secret code, the **Discord Bot Token**.

* **Task:** Ensure the `DISCORD_TOKEN` is set up as an **Environment Variable** on your hosting service. *Never* share this code or post it directly into a public file. This is the bot's password.

* * *

## 2. Housemate Ryker: Simplified Manual Testing Guide

Use this table to quickly verify that all core features and rule enforcements are working correctly in your server.

| Feature to Test | Step 1: Action (Type This Command or Message) | Step 2: Expected Result (What You Should See) |
| :--- | :--- | :--- |
| **Core Vibe Earning** | Send **three separate messages** in a general channel, waiting **15 seconds** between each one. | The messages stay in the chat. The bot should be silently giving you Vibe points. |
| **Profile Check** | Type: *!profile* | An embed (a large framed message) appears, showing your current **Flair**, **Nickname Icon**, Vibe Rank, and your Vibe Streak. |
| **Daily Streak** | Type: *!daily* | **(1)** A successful embed appears: *DAILY VIBE CLAIMED!* **(2)** Run *!daily* immediately again, and the bot sends an error about the time/date for the next claim. |
| **Admin Setup: Give Vibe** | *!vibe\_penalty @YourUsername -5000* (Note: The minus sign *removes* Vibe, so use a minus sign and a negative number to **add** Vibe). | Bot replies: *Vibe Penalty Applied...* You now have a high Vibe total for testing. |
| **Vibe Shop** | Type: *!shop* | An embed appears listing all items, their costs, and their ID numbers (1, 2, 3, etc.). |
| **Purchase Log** | *!buy 1* | **(1)** Bot replies: *PURCHASE SUCCESSFUL!* **(2)** A yellow/red alert embed appears in the **Mod Alerts Channel** detailing the purchase for admin follow-up. |
| **Fulfillment Tool** | *!set\_icon @YourUsername* ⭐ | Bot replies: *Icon Updated.* Run *!profile* to see the new ⭐ icon next to your name. |
| **Promotion Filter** | Send a message outside `#self-promo` like: *Hey everyone, subscribe to my youtube channel!* | Your message stays, but the bot immediately sends a **warning notification** telling you to use the correct channel. |
| **Spam Link Filter** | Send a message containing a suspicious link: *Check this out: bit.ly/spamurl* | **(1) Your message is immediately deleted.** **(2)** The bot briefly posts a temporary **removal notice** in the channel. |
| **Content Filter** | Send a message containing a forbidden keyword (e.g., one of the keywords listed in the *housemate\_ryker.py* Control Panel). | **(1) Your message is immediately deleted.** **(2)** The bot briefly posts a temporary **removal notice** in the channel. |
| **Admin Announcement** | *!say \#general **This is an announcement.*** | Your command message is **deleted**, and the bot posts the bolded message to the \#general channel. |
| **Reporting Tool** | *!report @YourUsername Test Reason* | Bot sends a confirmation to your DMs, and a **User Report** embed appears in the **Mod Alerts Channel**. |
