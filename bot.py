import asyncio
import base64
import copy
import importlib.metadata
import os
import re
import shutil
import tempfile
from urllib.parse import quote, urlparse

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from reminders import ReminderManager, reminder_scheduler


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")

YOUTUBE_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE")
YOUTUBE_COOKIES_B64 = os.getenv("YOUTUBE_COOKIES_B64")
YOUTUBE_BROWSER = os.getenv("YOUTUBE_BROWSER")
YOUTUBE_BROWSER_PATH = os.getenv("YOUTUBE_BROWSER_PATH", "/usr/bin/chromium")
YOUTUBE_PROXY = os.getenv("YOUTUBE_PROXY")
# Optional Webshare YouTube Proxy settings. The dedicated YouTube proxy plan
# supplies an endpoint, username, password, and port.
YOUTUBE_PROXY_ENDPOINT = os.getenv("YOUTUBE_PROXY_ENDPOINT")
YOUTUBE_PROXY_PORT = os.getenv("YOUTUBE_PROXY_PORT", "30000")
YOUTUBE_PROXY_USERNAME = os.getenv("YOUTUBE_PROXY_USERNAME")
YOUTUBE_PROXY_PASSWORD = os.getenv("YOUTUBE_PROXY_PASSWORD")
YOUTUBE_PROXY_SESSION = os.getenv("YOUTUBE_PROXY_SESSION", "elimini")
REMINDERS_DB_PATH = os.getenv("REMINDERS_DB_PATH", "reminders.db")
REMINDER_MAX_NAME_LENGTH = 100
REMINDER_MAX_AMOUNT = 100_000

TEMP_VC_CATEGORY_NAME = "Eli-Mini Temporary VCs"
TEMP_VC_INACTIVITY_SECONDS = 180
_temp_vc_delete_tasks: dict[int, asyncio.Task[None]] = {}

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
        if DISCORD_GUILD_ID:
            guild = discord.Object(id=int(DISCORD_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"Synced {len(synced)} commands to guild {DISCORD_GUILD_ID}")
        else:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} global commands")


bot = EliMini()
reminder_manager = ReminderManager(REMINDERS_DB_PATH)
_reminder_scheduler_task: asyncio.Task[None] | None = None


def _cancel_temp_vc_timer(channel_id: int) -> None:
    task = _temp_vc_delete_tasks.pop(channel_id, None)
    if task is not None and not task.done():
        task.cancel()


def _temp_vc_has_humans(channel: discord.VoiceChannel) -> bool:
    return any(not member.bot for member in channel.members)


def _schedule_temp_vc_deletion(channel: discord.VoiceChannel) -> None:
    _cancel_temp_vc_timer(channel.id)
    if not _temp_vc_has_humans(channel):
        _temp_vc_delete_tasks[channel.id] = asyncio.create_task(
            _delete_temp_vc_after_inactivity(channel.id)
        )


async def _delete_temp_vc_after_inactivity(channel_id: int) -> None:
    try:
        await asyncio.sleep(TEMP_VC_INACTIVITY_SECONDS)

        channel = bot.get_channel(channel_id)
        if not isinstance(channel, discord.VoiceChannel):
            return

        # Re-check immediately before deletion so a recently joined user keeps it.
        if _temp_vc_has_humans(channel):
            return

        await channel.delete(reason="Temporary voice channel inactive for 3 minutes.")
    except asyncio.CancelledError:
        return
    except discord.NotFound:
        return
    except discord.Forbidden:
        print(
            f"Could not delete temporary voice channel {channel_id}: "
            "missing Manage Channels permission."
        )
    except discord.HTTPException as exc:
        print(
            f"Could not delete temporary voice channel {channel_id}: "
            f"Discord returned an HTTP error: {exc}"
        )
    finally:
        task = _temp_vc_delete_tasks.get(channel_id)
        if task is asyncio.current_task():
            _temp_vc_delete_tasks.pop(channel_id, None)


async def _get_temp_vc_category(guild: discord.Guild) -> discord.CategoryChannel:
    category = discord.utils.get(
        guild.categories,
        name=TEMP_VC_CATEGORY_NAME,
    )
    if category is not None:
        return category

    return await guild.create_category(
        TEMP_VC_CATEGORY_NAME,
        reason="Create category for Eli-Mini temporary voice channels.",
    )


REMINDER_TIME_CHOICES = [
    app_commands.Choice(name="hours", value="hours"),
    app_commands.Choice(name="days", value="days"),
    app_commands.Choice(name="weeks", value="weeks"),
    app_commands.Choice(name="years", value="years"),
]


@bot.event
async def on_ready() -> None:
    global _reminder_scheduler_task

    if _reminder_scheduler_task is None or _reminder_scheduler_task.done():
        _reminder_scheduler_task = asyncio.create_task(
            reminder_scheduler(bot, reminder_manager)
        )

    if bot.user is not None:
        provider_version = _package_version("yt-dlp-getpot-wpc")
        chromium = shutil.which("chromium") or YOUTUBE_BROWSER_PATH
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
        print(f"yt-dlp: {yt_dlp.version.__version__}")
        print(f"yt-dlp-getpot-wpc: {provider_version or 'not installed'}")
        print(f"Chromium: {chromium}")
        print(
            "YouTube proxy: "
            f"{'configured' if _get_youtube_proxy() else 'not configured'}"
        )

        for guild in bot.guilds:
            category = discord.utils.get(
                guild.categories,
                name=TEMP_VC_CATEGORY_NAME,
            )
            if category is None:
                continue

            for channel in category.voice_channels:
                if _temp_vc_has_humans(channel):
                    _cancel_temp_vc_timer(channel.id)
                else:
                    _schedule_temp_vc_deletion(channel)


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


def _get_youtube_proxy() -> str | None:
    if YOUTUBE_PROXY:
        return YOUTUBE_PROXY

    if (
        YOUTUBE_PROXY_ENDPOINT
        and YOUTUBE_PROXY_USERNAME
        and YOUTUBE_PROXY_PASSWORD
    ):
        username = YOUTUBE_PROXY_USERNAME
        if YOUTUBE_PROXY_SESSION:
            username = f"{username}-{YOUTUBE_PROXY_SESSION}"

        return (
            f"http://{quote(username, safe="")}:"
            f"{quote(YOUTUBE_PROXY_PASSWORD, safe="")}@"
            f"{YOUTUBE_PROXY_ENDPOINT}:{YOUTUBE_PROXY_PORT}"
        )

    return None


def _build_ytdl_options(player_clients: list[str], use_cookies: bool) -> dict:
    options = copy.deepcopy(BASE_YTDL_OPTIONS)
    youtube_proxy = _get_youtube_proxy()
    if youtube_proxy:
        options["proxy"] = youtube_proxy

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
                "YouTube is still rejecting the extraction IP as a bot. "
                "The configured cookies/session did not bypass the challenge. "
                "If using YOUTUBE_PROXY, make sure the browser session/cookies match that proxy IP."
            )
        raise RuntimeError(
            "YouTube is rejecting the extraction IP as a bot. "
            "Set YOUTUBE_PROXY to a proxy/network where YouTube access works, "
            "or provide a matching YouTube cookie session."
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
    target_channel: discord.VoiceChannel | None = None,
) -> discord.VoiceClient:
    if interaction.guild is None:
        raise RuntimeError("This command can only be used inside a Discord server.")

    if target_channel is None:
        member = interaction.user
        voice_state = getattr(member, "voice", None)
        if voice_state is None or voice_state.channel is None:
            raise RuntimeError(
                "You are not in a voice channel. Choose a channel with /join channel:."
            )
        target_channel = voice_state.channel

    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if voice_client is None:
        voice_client = await target_channel.connect()
    elif voice_client.channel != target_channel:
        await voice_client.move_to(target_channel)

    return voice_client


@bot.tree.command(
    name="reminder",
    description="DM you a named reminder after a chosen amount of time.",
)
@app_commands.describe(
    name="The name/text of the reminder.",
    amount="How many units from now.",
    unit="Hours, days, weeks, or years.",
)
@app_commands.choices(unit=REMINDER_TIME_CHOICES)
async def reminder(
    interaction: discord.Interaction,
    name: str,
    amount: app_commands.Range[int, 1, REMINDER_MAX_AMOUNT],
    unit: app_commands.Choice[str],
) -> None:
    reminder_name = name.strip()
    if not reminder_name:
        await interaction.response.send_message(
            "❌ Please give the reminder a name."
        )
        return
    if len(reminder_name) > REMINDER_MAX_NAME_LENGTH:
        await interaction.response.send_message(
            f"❌ The reminder name must be {REMINDER_MAX_NAME_LENGTH} characters or fewer."
        )
        return

    reminder_id, fire_at = reminder_manager.create(
        interaction.user.id,
        reminder_name,
        amount,
        unit.value,
        "reminder",
    )

    await interaction.response.send_message(
        f"✅ Reminder **#{reminder_id} — {reminder_name}** set for "
        f"<t:{int(fire_at.timestamp())}:F> (<t:{int(fire_at.timestamp())}:R>). "
        "I’ll DM you when it is due."
    )


@bot.tree.command(
    name="alarm",
    description="DM you an alarm after a chosen amount of time.",
)
@app_commands.describe(
    name="The name/text of the alarm.",
    amount="How many units from now.",
    unit="Hours, days, weeks, or years.",
)
@app_commands.choices(unit=REMINDER_TIME_CHOICES)
async def alarm(
    interaction: discord.Interaction,
    name: str,
    amount: app_commands.Range[int, 1, REMINDER_MAX_AMOUNT],
    unit: app_commands.Choice[str],
) -> None:
    alarm_name = name.strip()
    if not alarm_name:
        await interaction.response.send_message(
            "❌ Please give the alarm a name."
        )
        return
    if len(alarm_name) > REMINDER_MAX_NAME_LENGTH:
        await interaction.response.send_message(
            f"❌ The alarm name must be {REMINDER_MAX_NAME_LENGTH} characters or fewer."
        )
        return

    alarm_id, fire_at = reminder_manager.create(
        interaction.user.id,
        alarm_name,
        amount,
        unit.value,
        "alarm",
    )

    await interaction.response.send_message(
        f"✅ Alarm **#{alarm_id} — {alarm_name}** set for "
        f"<t:{int(fire_at.timestamp())}:F> (<t:{int(fire_at.timestamp())}:R>). "
        "I’ll DM you when it is due."
    )


@bot.tree.command(
    name="reminders",
    description="List your pending reminders and alarms.",
)
async def reminders(interaction: discord.Interaction) -> None:
    items = reminder_manager.get_user_reminders(interaction.user.id)

    if not items:
        await interaction.response.send_message(
            "You do not have any pending reminders or alarms."
        )
        return

    lines = []
    for item in items:
        fire_at = str(item["fire_at"])
        lines.append(
            f"**#{item['id']}** · "
            f"{'🚨' if item['kind'] == 'alarm' else '⏰'} "
            f"**{item['name']}** · <t:{int(__import__('datetime').datetime.fromisoformat(fire_at).timestamp())}:R>"
        )

    await interaction.response.send_message(
        "**Your pending reminders:**\n" + "\n".join(lines)
    )


@bot.tree.command(
    name="cancelreminder",
    description="Cancel one of your pending reminders or alarms.",
)
@app_commands.describe(reminder_id="The ID shown by /reminders.")
async def cancelreminder(
    interaction: discord.Interaction,
    reminder_id: app_commands.Range[int, 1, 2_147_483_647],
) -> None:
    if reminder_manager.cancel(reminder_id, interaction.user.id):
        await interaction.response.send_message(
            f"✅ Cancelled reminder/alarm **#{reminder_id}**."
        )
    else:
        await interaction.response.send_message(
            f"❌ I couldn't find **#{reminder_id}** on your account."
        )


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


@bot.tree.command(name="join", description="Join a voice channel.")
@app_commands.describe(channel="The voice channel to join. Leave empty to join your current channel.")
async def join(
    interaction: discord.Interaction,
    channel: discord.VoiceChannel | None = None,
) -> None:
    try:
        voice_client = await get_or_create_voice_client(interaction, channel)
        channel_name = (
            voice_client.channel.name
            if voice_client.channel is not None
            else "the voice channel"
        )
        await interaction.response.send_message("🔊 Joined **" + channel_name + "**.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "I do not have permission to view or connect to that voice channel."
        )
    except (discord.ClientException, RuntimeError) as exc:
        await interaction.response.send_message(
            "❌ Could not join the voice channel: " + str(exc)
        )


@bot.tree.command(
    name="tempvc",
    description="Create a temporary voice channel that deletes after 3 minutes empty.",
)
@app_commands.describe(name="The name for your temporary voice channel")
async def tempvc(interaction: discord.Interaction, name: str) -> None:
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used inside a Discord server."
        )
        return

    channel_name = name.strip()
    if not channel_name:
        await interaction.response.send_message(
            "❌ Please provide a name for the temporary voice channel."
        )
        return

    if len(channel_name) > 100:
        await interaction.response.send_message(
            "❌ The channel name must be 100 characters or fewer."
        )
        return

    try:
        category = await _get_temp_vc_category(interaction.guild)
        channel = await interaction.guild.create_voice_channel(
            channel_name,
            category=category,
            reason=f"Temporary VC created by {interaction.user} ({interaction.user.id}).",
        )
        _schedule_temp_vc_deletion(channel)

        await interaction.response.send_message(
            f"✅ Created {channel.mention}. It will be deleted after "
            f"{TEMP_VC_INACTIVITY_SECONDS // 60} minutes with nobody connected."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I need the **Manage Channels** permission to create temporary voice channels."
        )
    except discord.HTTPException as exc:
        await interaction.response.send_message(
            f"❌ I couldn't create the temporary voice channel: {exc}"
        )




@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> None:
    """Start/cancel the three-minute empty-channel timer."""
    channels: list[discord.VoiceChannel] = []

    if isinstance(before.channel, discord.VoiceChannel):
        channels.append(before.channel)
    if (
        isinstance(after.channel, discord.VoiceChannel)
        and (before.channel is None or before.channel.id != after.channel.id)
    ):
        channels.append(after.channel)

    for channel in channels:
        if channel.category_id is None:
            continue

        category = discord.utils.get(
            channel.guild.categories,
            id=channel.category_id,
        )
        if category is None or category.name != TEMP_VC_CATEGORY_NAME:
            continue

        if _temp_vc_has_humans(channel):
            _cancel_temp_vc_timer(channel.id)
        else:
            _schedule_temp_vc_deletion(channel)

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
