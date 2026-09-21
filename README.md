# Eli-Mini

A simple Discord bot built with Python and [discord.py](https://discordpy.readthedocs.io/).

## Commands

- `/ping` — checks that the bot is online.
- `/hello` — greets a user.
- `/about` — shows basic bot information.
- `/play <youtube-url>` — joins your current voice channel and plays the YouTube video's audio.
- `/leave` — stops playback and leaves the voice channel.

## Setup

### 1. Create a Discord application

In the Discord Developer Portal:

1. Create a new application.
2. Open **Bot** and create the bot user.
3. Copy the bot token.
4. Keep the token private. Never commit it to Git.

The bot needs permission to **View Channel**, **Connect**, and **Speak** in the voice channel you want to use. The invite should include the **bot** and **applications.commands** scopes.

### 2. Install Python dependencies

Create a fresh virtual environment:

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

### 3. Install FFmpeg

FFmpeg must be installed separately and available on your system PATH because discord.py uses it to turn the extracted audio stream into Discord audio.

Verify it with:

```bash
ffmpeg -version
```

If FFmpeg is installed somewhere that is not on PATH, set `FFMPEG_PATH` in `.env` to the full path to the executable.

### 4. Configure the token

Copy `.env.example` to `.env`:

```text
DISCORD_TOKEN=your-real-token
FFMPEG_PATH=ffmpeg
```

Do not commit `.env`.

### 5. Configure YouTube playback

YouTube can return **"Sign in to confirm you're not a bot"** when yt-dlp requests playback. yt-dlp's current documentation recommends a PO Token Provider for affected clients, and Eli-Mini now includes the WebPoClient provider. urlyt-dlp PO Token Guidehttps://github.com/yt-dlp/yt-dlp/wiki/Po-Token-Guide

The repository now includes a Codespaces configuration that installs:

- Chromium
- FFmpeg
- `yt-dlp-getpot-wpc`

The provider automatically opens Chromium to mint the PO tokens required by yt-dlp. urlWebPoClient PO Token Providerhttps://github.com/coletdjnz/yt-dlp-getpot-wpc

**After pulling these changes into an existing Codespace, rebuild the container** so the new `.devcontainer/devcontainer.json` is applied. In VS Code/Codespaces, use **Command Palette → Codespaces: Rebuild Container**.

Then install/update Python dependencies:

```bash
python -m pip install -r requirements.txt
```

You normally do **not** need `YOUTUBE_BROWSER=chrome` or a cookies file with this setup. The default Chromium path is:

```text
YOUTUBE_BROWSER_PATH=/usr/bin/chromium
```

If Chromium is installed somewhere else, set `YOUTUBE_BROWSER_PATH` to its executable path.

### 6. Run Eli-Mini

```bash
python bot.py
```

### 7. Play a YouTube video

Join a voice channel, then run:

```text
/play url:https://www.youtube.com/watch?v=...
```

Eli-Mini will join your channel and start playing the video's audio. Running `/play` again stops the current track and starts the new one.

Use:

```text
/leave
```

to stop playback and disconnect.

## Notes

The bot uses yt-dlp to extract the playable media URL rather than downloading the video to disk. yt-dlp's YouTube support can change as YouTube changes its delivery requirements, so some videos or links may occasionally fail to extract.
