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
4. Keep the bot token private. Never commit it to Git.

The bot needs permission to **View Channel**, **Connect**, and **Speak** in the voice channel. The invite should include the **bot** and **applications.commands** scopes.

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
python -m pip install -r requirements.txt
```

### 3. Install FFmpeg

FFmpeg must be installed and available on PATH unless `FFMPEG_PATH` points to the executable.

Verify it with:

```bash
ffmpeg -version
```

### 4. Configure the token

Copy `.env.example` to `.env` and set your token:

```text
DISCORD_TOKEN=your-real-token
FFMPEG_PATH=ffmpeg
```

Do not commit `.env`.

### 5. YouTube playback in GitHub Codespaces

YouTube currently uses several anti-bot and Proof of Origin (PO) Token checks. yt-dlp's current guidance recommends PO Token Provider plugins for clients that require them. The WebPoClient provider can mint PO tokens in Chromium and is installed by this project.

The bot now tries several YouTube client paths:

1. `web_embedded`
2. `web_safari`
3. `mweb` with the WebPoClient PO-token provider
4. yt-dlp's default client

That fallback is deliberate: current YouTube behavior varies by client and by server IP. Recent yt-dlp reports also show `mweb` can still return `LOGIN_REQUIRED` on some datacenter IPs even when a PO-token provider is installed. urlyt-dlp PO Token Guidehttps://github.com/yt-dlp/yt-dlp/wiki/Po-Token-Guide

The Codespaces container installs:

- Chromium
- FFmpeg
- `yt-dlp-getpot-wpc`
- the current yt-dlp nightly containing recent YouTube client fixes

**For an existing Codespace:** rebuild the container after pulling these changes using **Command Palette → Codespaces: Rebuild Container**.

Then run:

```bash
python -m pip install -r requirements.txt
python bot.py
```

At startup Eli-Mini prints the installed yt-dlp version, WebPoClient version, and Chromium path. The WebPoClient README says a successful install appears as a PO Token provider in yt-dlp debug output and requires Chrome/Chromium. urlWebPoClient PO Token Providerhttps://github.com/coletdjnz/yt-dlp-getpot-wpc

### 6. If YouTube still says "Sign in to confirm you're not a bot"

A GitHub Codespaces server IP can still be challenged by YouTube. In that case, use a YouTube `cookies.txt` exported from a browser session and provide it to the Codespace as `YOUTUBE_COOKIES_B64`.

Do **not** commit the cookies file or put it in the repository.

The bot already supports:

```text
YOUTUBE_COOKIES_FILE=/absolute/path/to/cookies.txt
```

or:

```text
YOUTUBE_COOKIES_B64=<base64-encoded-cookies.txt>
```

On Windows PowerShell, after exporting `cookies.txt`, you can base64-encode it with:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("cookies.txt"))
```

Paste the resulting value into a Codespaces secret/environment variable named `YOUTUBE_COOKIES_B64`.

### 7. Run Eli-Mini

```bash
python bot.py
```

### 8. Play a YouTube video

Join a voice channel, then run:

```text
/play url:https://www.youtube.com/watch?v=...
```

Eli-Mini joins your channel and starts playing the video's audio. Running `/play` again stops the current track and starts the new one.

Use:

```text
/leave
```

to stop playback and disconnect.

## Notes

The bot uses yt-dlp to extract a playable media URL rather than downloading the video to disk. YouTube changes its delivery and anti-bot systems frequently, so server-side YouTube playback can occasionally break and require a new yt-dlp/provider update.
