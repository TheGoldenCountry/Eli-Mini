# Eli-Mini

A simple Discord bot built with Python and [discord.py](https://discordpy.readthedocs.io/).

## Commands

- `/ping` — checks that the bot is online.
- `/hello` — greets a user.
- `/about` — shows basic bot information.
- `/join [channel]` — joins the selected voice channel, or your current voice channel if none is selected.
- `/tempvc <name>` — creates a named temporary voice channel in the `Eli-Mini Temporary VCs` category. The channel is deleted after 3 minutes with no human members connected.
- `/reminder <name> <amount> <unit>` — schedules a one-shot reminder and DMs you when it is due. Units are hours, days, weeks, or years (365 days).
- `/alarm <name> <amount> <unit>` — schedules a one-shot alarm and DMs you when it is due.
- `/reminders` — lists your pending reminders and alarms.
- `/cancelreminder <reminder-id>` — cancels one of your pending reminders or alarms.
- `/play <youtube-url>` — joins your current voice channel and plays the YouTube video's audio.
- `/leave` — stops playback and leaves the voice channel.

## Setup

### 1. Create a Discord application

In the Discord Developer Portal:

1. Create a new application.
2. Open **Bot** and create the bot user.
3. Copy the bot token.
4. Keep the bot token private. Never commit it to Git.

The bot needs permission to **View Channel**, **Connect**, **Speak**, and **Manage Channels**. **Manage Channels** is required for `/tempvc` to create and delete channels. The invite should include the **bot** and **applications.commands** scopes.

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

### 5. Reminders and alarms

Reminders and alarms are stored in a local SQLite database (`reminders.db`) so they survive normal bot restarts. They use a relative delay from the time you run the command. For example:

```text
/reminder name:Homework amount:2 unit:hours
/alarm name:Wake up amount:1 unit:days
```

The bot sends these directly to your Discord DMs, so your account must allow DMs from the bot. The scheduled timestamp is shown using Discord's localized timestamp display.

Discord's standard bot API does not provide `discord.py` bots with a way to initiate a one-to-one DM voice call. For that reason, an `/alarm` sends the alarm DM and tells you to open the DM and start the call yourself. Discord's user-facing documentation describes DM voice calls as being started from the Discord client. citehttps://support.discord.com/hc/en-us/articles/360041721052-Video-Calls

### 6. YouTube playback in GitHub Codespaces

YouTube currently uses several anti-bot and Proof of Origin (PO) Token checks. yt-dlp's current guidance recommends PO Token Provider plugins for clients that require them. The WebPoClient provider can mint PO tokens in Chromium and is installed by this project. urlyt-dlp PO Token Guidehttps://github.com/yt-dlp/yt-dlp/wiki/Po-Token-Guide

This project uses the **current yt-dlp PO-token provider API** through `yt-dlp-getpot-wpc`. The old `yt-dlp-get-pot` framework is deprecated and is intentionally **not** installed. The WPC provider's current source imports yt-dlp's built-in PO-token provider classes directly. urlWebPoClient PO Token Providerhttps://github.com/coletdjnz/yt-dlp-getpot-wpc urlDeprecated GetPOT frameworkhttps://github.com/coletdjnz/yt-dlp-get-pot

The bot tries several YouTube client paths:

1. `web_embedded`
2. `web_safari`
3. `mweb` with the WebPoClient PO-token provider
4. yt-dlp's default client

That fallback is deliberate: current YouTube behavior varies by client and by server IP. The current yt-dlp PO Token Guide notes that `web_safari` can expose HLS formats that do not currently require a GVS PO token, while `mweb` requires one for GVS. urlyt-dlp PO Token Guidehttps://github.com/yt-dlp/yt-dlp/wiki/Po-Token-Guide

The Codespaces container installs:

- Chromium
- FFmpeg
- `yt-dlp-getpot-wpc`
- yt-dlp

**For an existing Codespace:** rebuild the container after pulling these changes using **Command Palette → Codespaces: Rebuild Container**. This project deliberately uses Python 3.12 because the current WebPoClient dependency chain has a known import failure under Python 3.14. After rebuilding, verify that `python --version` reports Python 3.12.x and that `which python` points into `.venv/bin/python`. urlWebPoClient Python 3.14 import issuehttps://github.com/coletdjnz/yt-dlp-getpot-wpc/issues/7

### 7. Verify the PO-token provider

In the Codespace, run:

```bash
git pull origin main
python -m pip uninstall -y yt-dlp-get-pot
python -m pip install -U -r requirements.txt
python -m yt_dlp -v "https://www.youtube.com/watch?v=PKcpv05bHbc" 2>&1 | grep -i "PO Token Providers"
```

With the current WPC provider loaded, the yt-dlp documentation says the verbose output should include a provider such as:

```text
[debug] [youtube] [pot] PO Token Providers: wpc-1.1.2 (external)
```

The WebPoClient package requires yt-dlp 2025.09.26 or newer and Chrome/Chromium. urlWebPoClient PO Token Providerhttps://github.com/coletdjnz/yt-dlp-getpot-wpc

If the output still says `none`, check the same Python environment explicitly:

```bash
python -m pip show yt-dlp
python -m pip show yt-dlp-getpot-wpc
python -c "import yt_dlp_plugins.extractor.getpot_wpc as wpc; print(wpc.__file__)"
```

Those commands distinguish a missing package from a provider-loading problem.

### 8. If YouTube still says "Sign in to confirm you're not a bot"

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

### 9. Run Eli-Mini

```bash
python bot.py
```

### 10. Play a YouTube video

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
