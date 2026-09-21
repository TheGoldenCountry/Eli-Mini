# Eli-Mini

A simple Discord bot built with Python and [discord.py](https://discordpy.readthedocs.io/).

## What it does

The starter bot currently provides three slash commands:

- `/ping` — checks that the bot is online.
- `/hello` — greets a user.
- `/about` — shows basic bot information.

## Setup

### 1. Create a Discord application

In the Discord Developer Portal:

1. Create a new application.
2. Open **Bot** and create the bot user.
3. Copy the bot token.
4. Keep the token private. Never commit it to Git.

### 2. Install dependencies

Create a fresh virtual environment, then run:

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\\Scripts\\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

### 3. Configure the token

Copy `.env.example` to `.env`:

```text
DISCORD_TOKEN=your-real-token
```

Do not commit `.env`.

### 4. Invite the bot

Generate an OAuth2 invite URL for your application with the **bot** and **applications.commands** scopes. Give it only the permissions it actually needs.

### 5. Run Eli-Mini

```bash
python bot.py
```

When it connects, you should see a login message. Then use `/ping`, `/hello`, or `/about` in a server where the bot is installed.

## Next steps

This is intentionally small. The next stage can move commands into a `cogs/` package and put the actual Eli-Mini functionality behind one or more commands.
