🏡 Housemate Ryker: The GuysNextDoor Community Manager
Housemate Ryker is a custom-built Discord bot designed for the GuysNextDoor community. Its primary function is to automate moderation, drive member engagement, and provide a stable, feature-rich environment.

This bot is engineered for 24/7 uptime using a Web Service hosting model to prevent the "sleeping bot" issues common on free hosting platforms.

✨ Core Features (Vibe Economy 2.0)
Housemate Ryker now runs a complete, persistent economy with user customization and strong moderation tools:

|

| Feature | Description | On-Brand Terminology |
| Verification System | Automatically grants the Member role to users who react to the rules message. | New Neighbor Welcome |
| Vibe (XP) System | Rewards users for sending messages (1-3 Vibe) with a 15-second cooldown to prevent spam. | Moving Up The Block |
| Daily Streak | Users can claim a daily Vibe bonus that increases with their consecutive streak. | Daily Chores |
| Profile Customization | Allows users to buy permanent profile icons and flairs visible on !profile. | Personalize Your Property |
| Anti-Spam/Promotion | Auto-filters suspicious links and promotional messages outside of designated channels. | Keep the Street Clean |
| Prestige System | End-game feature allowing max-rank users to reset Vibe for a permanent Legacy Resident tier. | Achieving Legacy Status |

📈 Neighborhood Ranks and Prestige Tiers
The bot manages and grants the following cosmetic roles automatically. The Vibe threshold has been increased to support the new economy.

| Vibe Required | Rank Role Name |
| 1 - 100 Vibe | New Neighbor |
| 101 - 250 Vibe | Familiar Face |
| 251 - 500 Vibe | Resident |
| 501 - 2000 Vibe | Housemate |
| 2000+ Vibe | Block Captain (Max Rank for Prestige) |

Prestige Tiers: Legacy Resident I, Legacy Resident II, etc. (Permanent status gained via !prestige).

🤖 User Commands
| Command | Category | Description |
| !profile | Vibe | Displays full user stats, including Vibe, Rank, Streak, and purchased Custom Icon/Flair. |
| !daily | Vibe | Claims the daily Vibe bonus and maintains the streak. |
| !rank | Vibe | Shows Vibe count and progress to the next level. |
| !leaderboard | Vibe | Shows the top 10 members with the highest Vibe. |
| !prestige | Vibe | Resets Vibe at max rank (2000+) to earn a permanent Prestige Tier. |
| !shop / !buy <ID> | Economy | Displays and purchases exclusive profile perks and creator interactions. |
| !report <@user> <reason> | Safety | Confidentially reports a user to the moderation team. |
| !nom_vote <@user> | Community | Casts a vote for the Neighbor of the Month. |

🛡️ Administrative Commands (Moderator Use)
| Command | Purpose | Fulfillment Type |
| !vibe_penalty | Deducts Vibe from a user and logs the action in the user's history. | Moderation |
| !set_icon @user <emoji> | Fulfills Vibe Shop Item #1. Sets the user's permanent profile icon. | Fulfillment |
| !set_flair @user <text> | Fulfills Vibe Shop Item #2. Sets the user's permanent custom flair. | Fulfillment |
| !say #channel <message> | Posts a custom, markdown-formatted message to any specified channel. | Utility |
| !nom_winner | Calculates and announces the winner of the Neighbor of the Month vote. | Utility |

⚙️ Setup and Deployment
This project remains configured for 24/7 deployment on Render as a Web Service.

Start Command: gunicorn housemate_ryker:app

Discord Setup: Requires roles: Member, New Neighbor, Familiar Face, Resident, Housemate, Block Captain, and Prestige Roles (Legacy Resident I, etc.).

Created by the GuysNextDoor Team.
