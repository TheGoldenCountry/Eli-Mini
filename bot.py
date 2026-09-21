import asyncio
import base64
import copy
import importlib.metadata
import os
import re
import shutil
import tempfile
from urllib.parse import urlparse

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

YOUTUBE_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE")
YOUTUBE_COOKIES_B64 = os.getenv("YOUTUBE_COOKIES_B64")
YOUTUBE_BROWSER = os.getenv("YOUTUBE_BROWSER")
YOUTUBE_BROWSER_PATH = os.getenv("YOUTUBE_BROWSER_PATH", "/usr/bin/chromium")

# YouTube currently has a known failure where authenticated sessions select
# tv_downgraded and return "The page needs to be reloaded". The upstream
# workaround is to try default + web_embedded first. Some sessions still
# reject authenticated extraction, so we also retry without cookies.
YOUTUBE_CLIENT_PROFILES = (
    ("default+web_embedded", ["default", "web_embedded"], True),
    ("web_embedded (no cookies)", ["web_embedded"], False),
    ("web_safari (no cookies)", ["web_safari"], False),
    ("mweb (no cookies)", ["mweb"], False),
)


BASE_YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
}


class EliMini(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await self.tree.sync()


bot = EliMini()


@bot.event
async def on_ready() -> None:
    if bot.user is not None:
        provider_version = _package_version("yt-dlp-getpot-wpc")
        chromium = shutil.which("chromium") or YOUTUBE_BROWSER_PATH
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
        print(f"yt-dlp: {yt_dlp.version.__version__}")
        print(f"yt-dlp-getpot-wpc: {provider_version or 'not installed'}")
        print(f"Chromium: {chromium}")


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"youtube.com", "www.youtube.com", "youtu.be", "music.youtube.com"}


def _clean_error(message: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", message)


def _build_ytdl_options(player_clients: list[str], use_cookies: bool) -> dict:
    options = copy.deepcopy(BASE_YTDL_OPTIONS)
    options["extractor_args"] = {
        "youtube": {
            "player_client": player_clients,
        }
    }
    options["extractor_args"]["youtubepot-wpc"] = {
        "browser_path": YOUTUBE_BROWSER_PATH,
    }

    if not use_cookies:
        return options

    if YOUTUBE_COOKIES_FILE:
        options["cookiefile"] = YOUTUBE_COOKIES_FILE
    elif YOUTUBE_COOKIES_B64:
        try:
            cookie_bytes = base64.b64decode(YOUTUBE_COOKIES_B64, validate=True)
        except Exception as exc:
            raise RuntimeError("YOUTUBE_COOKIES_B64 is not valid base64.") from exc

        cookie_file = tempfile.NamedTemporaryFile(
            mode="wb", suffix=".txt", delete=False
        )
        try:
            cookie_file.write(cookie_bytes)
            cookie_file.close()
        except Exception:
            cookie_file.close()
            os.remove(cookie_file.name)
            raise

        options["cookiefile"] = cookie_file.name
    elif YOUTUBE_BROWSER:
        options["cookiesfrombrowser"] = (YOUTUBE_BROWSER, None, None, None)

    return options


def extract_audio(url: str) -> tuple[str, str]:
    last_error = "yt-dlp could not find a playable audio stream."
    errors: list[str] = []

    for profile_name, player_clients, use_cookies in YOUTUBE_CLIENT_PROFILES:
        temporary_cookie_file: str | None = None
        try:
            options = _build_ytdl_options(player_clients, use_cookies)
            cookie_path = options.get("cookiefile")
            if (
                use_cookies
                and YOUTUBE_COOKIES_B64
                and cookie_path
                and cookie_path != YOUTUBE_COOKIES_FILE
            ):
                temporary_cookie_file = cookie_path

            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=False)

            if info and info.get("url"):
                return info.get("title", "YouTube audio"), info["url"]

            last_error = f"{profile_name}: no playable stream"
            errors.append(last_error)

        except yt_dlp.utils.DownloadError as exc:
            last_error = _clean_error(str(exc))
            errors.append(f"{profile_name}: {last_error}")
            continue
        finally:
            if temporary_cookie_file:
                try:
                    os.remove(temporary_cookie_file)
                except OSError:
                    pass

    if "Sign in to confirm" in last_error or "not a bot" in last_error:
        if YOUTUBE_COOKIES_FILE or YOUTUBE_COOKIES_B64 or YOUTUBE_BROWSER:
            raise RuntimeError(
                "YouTube is still rejecting the Codespaces IP as a bot. "
                "The configured browser/cookie session did not bypass the challenge."
            )
        raise RuntimeError(
            "YouTube is rejecting the Codespaces server IP as a bot. "
            "Add YOUTUBE_COOKIES_B64 from a YouTube session."
        )

    if "The page needs to be reloaded" in last_error:
        raise RuntimeError(
            "YouTube rejected every player client. "
            'It returned "The page needs to be reloaded." '
            f"Clients tried: {', '.join(errors)}"
        )

    raise RuntimeError(last_error)


async def get_or_create_voice_client(
    interaction: discord.Interaction,
) -> discord.VoiceClient:
    if interaction.guild is None:
        raise RuntimeError("This command can only be used inside a Discord server.")

    member = interaction.user
    voice_state = getattr(member, "voice", None)
    if voice_state is None or voice_state.channel is None:
        raise RuntimeError("Join a voice channel first, then run /play.")

    target_channel = voice_state.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if voice_client is None:
        voice_client = await target_channel.connect()
    elif voice_client.channel != target_channel:
        await voice_client.move_to(target_channel)

    return voice_client


@bot.tree.command(name="ping", description="Check whether Eli-Mini is online.")
async def ping(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Pong! 🏓")


@bot.tree.command(name="hello", description="Say hello to Eli-Mini.")
@app_commands.describe(name="The person to greet")
async def hello(interaction: discord.Interaction, name: str | None = None) -> None:
    target = name or interaction.user.display_name
    await interaction.response.send_message(f"Hello, {target}! 👋")


@bot.tree.command(name="about", description="Show basic information about Eli-Mini.")
async def about(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        "I'm Eli-Mini, a simple Discord bot built with Python and discord.py."
    )


@bot.tree.command(name="play", description="Join your voice channel and play a YouTube link.")
@app_commands.describe(url="A YouTube video URL")
async def play(interaction: discord.Interaction, url: str) -> None:
    await interaction.response.defer(thinking=True)

    if not is_youtube_url(url):
        await interaction.followup.send(
            "Please give me a YouTube link, such as https://www.youtube.com/watch?v=..."
        )
        return

    try:
        voice_client = await get_or_create_voice_client(interaction)
        title, stream_url = await asyncio.to_thread(extract_audio, url)

        if voice_client.is_playing():
            voice_client.stop()

        source = discord.FFmpegPCMAudio(
            stream_url,
            executable=FFMPEG_PATH,
            before_options=(
                "-reconnect 1 -reconnect_streamed 1 "
                "-reconnect_delay_max 5"
            ),
            options="-vn",
        )
        voice_client.play(source)

        await interaction.followup.send(f"▶️ Now playing **{title}**")
    except discord.Forbidden:
        await interaction.followup.send(
            "I don't have permission to join or speak in that voice channel."
        )
    except (discord.ClientException, RuntimeError) as exc:
        await interaction.followup.send(f"❌ I couldn't play that link: {exc}")


@bot.tree.command(name="leave", description="Stop playback and leave the voice channel.")
async def leave(interaction: discord.Interaction) -> None:
    voice_client = (
        discord.utils.get(bot.voice_clients, guild=interaction.guild)
        if interaction.guild is not None
        else None
    )

    if voice_client is None:
        await interaction.response.send_message("I'm not in a voice channel.")
        return

    voice_client.stop()
    await voice_client.disconnect()
    await interaction.response.send_message("👋 Left the voice channel.")


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not set. Put your bot token in .env or your environment."
    )

bot.run(TOKEN)
