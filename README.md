# 🏡 Housemate Ryker: The GuysNextDoor Community Manager

**Housemate Ryker** is a custom-built Discord bot designed for the GuysNextDoor community. Its primary function is to automate moderation, drive member engagement, and provide a stable, on-brand environment so that you, as the creator, can focus on content creation and personal goals.

This bot is engineered for 24/7 uptime using a **Web Service** hosting model to prevent the "sleeping bot" issues common on free hosting platforms.

## ✨ Core Features

Housemate Ryker handles all the heavy lifting, ensuring your server runs itself:

| Feature | Description | On-Brand Terminology |
| ----- | ----- | ----- |
| **Verification System** | Automatically grants the **Member** role to users who react to the rules message. | `New Neighbor Welcome` |
| **Vibe (XP) System** | Rewards users for sending messages with 1-3 Vibe points. Includes a **15-second cooldown** to prevent spam. | `Moving Up The Block` |
| **Automatic Leveling** | Automatically assigns and removes cosmetic roles when a member reaches a Vibe milestone. | `Neighborhood Ranks` |
| **Uptime Management** | Runs a Flask web server in a separate thread to ensure 24/7 uptime on hosting services like Render. | `Always Home` |

## 📈 Neighborhood Ranks (Vibe Levels)

The bot manages the following cosmetic roles automatically:

| Vibe Required | Rank Role Name |
| ----- | ----- |
| 1 - 100 Vibe | **New Neighbor** |
| 101 - 250 Vibe | **Familiar Face** |
| 251 - 500 Vibe | **Resident** |
| 501 - 1000 Vibe | **Housemate** |
| 1001+ Vibe | **Block Captain** |

## 🤖 User Commands

Members can interact with the leveling system using these commands:

| Command | Description |
| ----- | ----- |
| `!rank` | Displays the user's current Vibe count and their current neighborhood rank. |
| `!leaderboard` | Shows the top 10 members with the highest Vibe in the server. |

## ⚙️ Setup and Deployment (Render)

This project is specifically configured to be deployed on **Render** as a **Web Service** to guarantee continuous operation.

### 1. Prerequisites

1. A Discord Bot Token (added as an environment variable).

2. The following roles created in the Discord server (must match names exactly): `Member`, `New Neighbor`, `Familiar Face`, `Resident`, `Housemate`, `Block Captain`.

### 2. Files Overview

The following files are required for deployment:

| File | Purpose | Critical Element |
| ----- | ----- | ----- |
| `housemate_ryker.py` | Contains all bot logic, including the threading necessary to run the Discord Bot and Flask Web Server concurrently. | Runs Discord bot in a **background thread**. |
| `requirements.txt` | Lists all necessary Python packages. | Must include `discord.py`, `Flask`, and `gunicorn`. |
| `Procfile` | Instructs the hosting platform (Render) how to start the Web Service. | Uses `gunicorn` to run the Flask web server in the **main thread**. |

### 3. Critical Hosting Configuration

To achieve 24/7 uptime, the service must be deployed with the following settings on Render:

| Setting | Value | Rationale |
| ----- | ----- | ----- |
| **Service Type** | Web Service | Required for continuous uptime (Render's health checks). |
| **Build Command** | `pip install -r requirements.txt` | Installs all dependencies. |
| **Start Command** | `gunicorn housemate_ryker:app` | Executes the Flask server, which in turn starts the Discord bot in the background thread. |
| **Environment Variable** | `DISCORD_TOKEN` | Stores the secure bot token. |

*Created by the GuysNextDoor Team.*
