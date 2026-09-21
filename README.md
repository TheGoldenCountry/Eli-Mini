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

### 5. Configure YouTube authentication

YouTube may block yt-dlp with **"Sign in to confirm you're not a bot."** yt-dlp documents cookies as a workaround for these cases. urlyt-dlp's cookie FAQhttps://github.com/yt-dlp/yt-dlp/wiki/FAQ

**Important for GitHub Codespaces:** `YOUTUBE_BROWSER=chrome` only works when Chrome is actually installed in the same environment and has the relevant cookies. A normal Codespace does not have your Windows/Chrome profile, so point Eli-Mini at an exported cookies file instead.

For a Codespace/server, set:

```text
YOUTUBE_COOKIES_FILE=/absolute/path/to/cookies.txt
```

You can also keep the cookie file out of the working tree and load it through a Codespaces secret using a base64-encoded value:

```text
YOUTUBE_COOKIES_B64=<base64-encoded-cookies.txt>
```

The cookies file must be in Mozilla/Netscape format. yt-dlp notes that YouTube rotates cookies, so exported cookies may need to be refreshed periodically. urlyt-dlp's YouTube extractor documentationhttps://github.com/yt-dlp/yt-dlp/wiki/Extractors

**Never commit or publicly share YouTube cookies.** They are authentication credentials. Keep `cookies.txt` outside the repository, or store its base64 value as a private Codespaces secret.

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
