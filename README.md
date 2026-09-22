# Eli-Mini

A simple Discord bot built with Python, [discord.py](https://discordpy.readthedocs.io/), and [Wavelink](https://github.com/PythonistaGuild/Wavelink).

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
- `/play <youtube-url>` — joins your current voice channel and plays a YouTube video through Lavalink.
- `/leave` — stops playback and leaves the voice channel.

## Setup

### 1. Create a Discord application

In the Discord Developer Portal:

1. Create a new application.
2. Open **Bot** and create the bot user.
3. Copy the bot token.
4. Keep the bot token private. Never commit it to Git.

The bot needs permission to **View Channel**, **Connect**, **Speak**, and **Manage Channels**. **Manage Channels** is required for `/tempvc` to create and delete channels. The invite should include the **bot** and **applications.commands** scopes.

### 2. Codespaces environment

This project is configured for Python 3.12 and includes Java 21 in the dev container.

Rebuild the Codespace after pulling these changes:

**Command Palette → Codespaces: Rebuild Container**

The rebuild installs Wavelink and the Java runtime needed for Lavalink.

### 3. Configure the environment

Copy `.env.example` to `.env` and set:

```text
DISCORD_TOKEN=your-real-token
LAVALINK_URI=http://127.0.0.1:2333
LAVALINK_PASSWORD=eliminimini
```

Do not commit `.env`.

### 4. Lavalink

Eli-Mini now uses Lavalink instead of running yt-dlp/FFmpeg directly for YouTube playback.

The repository contains:

- `lavalink/application.yml` — local Lavalink server configuration.
- `scripts/start-lavalink.sh` — downloads Lavalink 4.2.2 on first use and starts it.
- `Wavelink 3.5.2` — the Python client used by Eli-Mini.
- `youtube-source 1.18.2` — the Lavalink YouTube plugin.

Lavalink 4.2.2 is the current stable Lavalink release, and Wavelink 3.5.2 includes Discord DAVE support. urlLavalink releaseshttps://github.com/lavalink-devs/Lavalink/releases urlWavelink releaseshttps://github.com/PythonistaGuild/Wavelink/releases

The Codespace normally starts Lavalink automatically when the container starts. To start it manually:

```bash
bash scripts/start-lavalink.sh
```

To run it in the background:

```bash
bash scripts/start-lavalink.sh --background
```

The background log is:

```text
lavalink/lavalink.log
```

### 5. YouTube playback

Lavalink uses the `youtube-source` plugin, which supports multiple YouTube InnerTube clients and can use OAuth as an optional authentication fallback. The plugin currently documents clients such as `WEB`, `MWEB`, `WEBEMBEDDED`, `ANDROID_VR`, and `TVHTML5_SIMPLY`. urlyoutube-source documentationhttps://github.com/lavalink-devs/youtube-source/blob/main/README.md

No YouTube proxy, exported browser cookie file, Chromium installation, yt-dlp executable, or local FFmpeg process is required by Eli-Mini's playback code.

This does **not** guarantee that YouTube will never challenge a Lavalink server. YouTube can change its anti-bot behavior. The advantage is that the YouTube extraction and audio transport are handled by Lavalink plus `youtube-source`, rather than by the Python bot directly.

### 6. Optional YouTube OAuth fallback

When YouTube continues to challenge the Lavalink server, `youtube-source` supports OAuth. Its documentation recommends using a burner account rather than a primary YouTube account and warns that OAuth is not a guaranteed solution. urlyoutube-source OAuth documentationhttps://github.com/lavalink-devs/youtube-source/blob/main/README.md#using-oauth-tokens

The repository leaves OAuth disabled by default.

To enable it:

1. Set `LAVALINK_YOUTUBE_OAUTH_ENABLED=true` in your Codespace environment.
2. Start Lavalink in the foreground with `bash scripts/start-lavalink.sh`.
3. Follow the device-code instructions printed by Lavalink.
4. Save the refresh token Lavalink gives you as a Codespaces secret named `LAVALINK_YOUTUBE_REFRESH_TOKEN`.
5. Add `refreshToken` to the `plugins.youtube.oauth` section in `lavalink/application.yml`.
6. Restart Lavalink and Eli-Mini.

Do not commit the refresh token.

### 7. Reminders and alarms

Reminders and alarms are stored in `reminders.db` so they survive normal bot restarts.

Examples:

```text
/reminder name:Homework amount:2 unit:hours
/alarm name:Wake Up amount:1 unit:days
```

The bot sends reminders directly to your Discord DMs. Discord must allow the bot to DM you.

### 8. Run Eli-Mini

With Lavalink running:

```bash
python bot.py
```

Then join a voice channel and run:

```text
/play url:https://www.youtube.com/watch?v=...
```

Running `/play` again replaces the current track.

Use:

```text
/leave
```

to stop playback and disconnect.

## Notes

Lavalink is a separate audio server process. Eli-Mini connects to the local node at `127.0.0.1:2333` by default.

YouTube changes its delivery and anti-bot systems frequently, so playback can still require updates to `youtube-source` or its configured client set.
