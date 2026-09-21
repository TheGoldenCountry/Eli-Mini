import asyncio
import os
from urllib.parse import urlparse

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

YTDL_OPTIONS = {
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
        # Register slash commands with Discord.
        await self.tree.sync()


bot = EliMini()


@bot.event
async def on_ready() -> None:
    if bot.user is not None:
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")


def is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"youtube.com", "www.youtube.com", "youtu.be", "music.youtube.com"}


def extract_audio(url: str) -> tuple[str, str]:
    """Return (title, direct_stream_url) for a YouTube URL."""
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info or not info.get("url"):
        raise RuntimeError("yt-dlp could not find an audio stream for that URL.")

    return info.get("title", "YouTube audio"), info["url"]


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
    except (discord.ClientException, RuntimeError, yt_dlp.utils.DownloadError) as exc:
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
