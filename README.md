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

YouTube can sometimes block yt-dlp with a message such as **"Sign in to confirm you're not a bot."** This can happen even for public videos. Current yt-dlp guidance supports supplying a browser session via cookies. urlyt-dlp's cookie FAQhttps://github.com/yt-dlp/yt-dlp/wiki/FAQ

For a bot running on the same computer as your browser, you can set:

```text
YOUTUBE_BROWSER=chrome
```

Replace `chrome` with the browser containing the YouTube session.

For a bot running on a VPS/server, export a YouTube cookies file in Netscape format and set:

```text
YOUTUBE_COOKIES_FILE=/absolute/path/to/cookies.txt
```

**Never commit `cookies.txt` to GitHub or share it.** Treat it like an authentication credential. The repository's `.gitignore` already ignores `.env`, but you should also keep your cookies file outside the repository.

Cookies may stop working as YouTube rotates sessions, so this is an operational workaround rather than a permanent guarantee.

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
