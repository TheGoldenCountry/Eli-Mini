import asyncio
import os
from urllib.parse import urlparse

import discord
import wavelink
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from reminders import ReminderManager, format_timestamp, reminder_scheduler


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")
LAVALINK_URI = os.getenv("LAVALINK_URI", "http://127.0.0.1:2333")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "eliminimini")
REMINDERS_DB_PATH = os.getenv("REMINDERS_DB_PATH", "reminders.db")
REMINDER_MAX_NAME_LENGTH = 100
REMINDER_MAX_AMOUNT = 100_000

TEMP_VC_CATEGORY_NAME = "Eli-Mini Temporary VCs"
TEMP_VC_INACTIVITY_SECONDS = 180
_temp_vc_delete_tasks: dict[int, asyncio.Task[None]] = {}

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

        try:
            await wavelink.Pool.connect(
                nodes=[
                    wavelink.Node(
                        identifier="local",
                        uri=LAVALINK_URI,
                        password=LAVALINK_PASSWORD,
                        retries=0,
                    )
                ],
                client=self,
            )
        except wavelink.WavelinkException as exc:
            print(
                "Lavalink is not available yet. Start Lavalink before using "
                f"/join or /play: {exc}"
            )


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
        print(f"Logged in as {bot.user} (ID: {bot.user.id})")
        print(f"Lavalink URI: {LAVALINK_URI}")

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


def is_youtube_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {
        "youtube.com",
        "www.youtube.com",
        "youtu.be",
        "music.youtube.com",
    }


async def _ensure_lavalink_node() -> wavelink.Node:
    try:
        node = wavelink.Pool.get_node("local")
        if node.status == wavelink.NodeStatus.CONNECTED:
            return node
    except wavelink.InvalidNodeException:
        pass

    await wavelink.Pool.connect(
        nodes=[
            wavelink.Node(
                identifier="local",
                uri=LAVALINK_URI,
                password=LAVALINK_PASSWORD,
                retries=0,
            )
        ],
        client=bot,
    )
    return wavelink.Pool.get_node("local")


async def get_or_create_voice_player(
    interaction: discord.Interaction,
    target_channel: discord.VoiceChannel | None = None,
) -> wavelink.Player:
    if interaction.guild is None:
        raise RuntimeError("This command can only be used inside a Discord server.")

    await _ensure_lavalink_node()

    if target_channel is None:
        voice_state = getattr(interaction.user, "voice", None)
        if voice_state is None or voice_state.channel is None:
            raise RuntimeError(
                "You are not in a voice channel. Choose a channel with /join channel:."
            )
        target_channel = voice_state.channel

    voice_client = interaction.guild.voice_client

    if isinstance(voice_client, wavelink.Player):
        if voice_client.channel != target_channel:
            await voice_client.move_to(target_channel)
        return voice_client

    if voice_client is not None:
        await voice_client.disconnect()

    return await target_channel.connect(cls=wavelink.Player)


@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload) -> None:
    print(f"Lavalink node ready: {payload.node.identifier}")


@bot.event
async def on_wavelink_track_exception(
    payload: wavelink.TrackExceptionEventPayload,
) -> None:
    print(
        "Lavalink track exception: "
        f"{payload.exception.message or payload.exception.cause or 'unknown error'}"
    )


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
            f"**{item['name']}** · {format_timestamp(fire_at)}"
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
        player = await get_or_create_voice_player(interaction, channel)
        channel_name = player.channel.name if player.channel is not None else "the voice channel"
        await interaction.response.send_message("🔊 Joined **" + channel_name + "**.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "I do not have permission to view or connect to that voice channel."
        )
    except (discord.ClientException, wavelink.WavelinkException, RuntimeError) as exc:
        await interaction.response.send_message(
            "❌ Could not join the voice channel: " + str(exc)
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
        player = await get_or_create_voice_player(interaction)

        search_result = await wavelink.Playable.search(
            url,
            source=wavelink.TrackSource.YouTube,
        )

        if not search_result:
            raise RuntimeError("Lavalink could not find that YouTube video.")

        if isinstance(search_result, wavelink.Playlist):
            if not search_result.tracks:
                raise RuntimeError("Lavalink returned an empty YouTube playlist.")
            track = search_result.tracks[0]
        else:
            track = search_result[0]

        await player.play(track, replace=True)
        await interaction.followup.send(f"▶️ Now playing **{track.title}**")
    except discord.Forbidden:
        await interaction.followup.send(
            "I don't have permission to join or speak in that voice channel."
        )
    except (discord.ClientException, wavelink.WavelinkException, RuntimeError) as exc:
        await interaction.followup.send(f"❌ I couldn't play that link: {exc}")


@bot.tree.command(name="leave", description="Stop playback and leave the voice channel.")
async def leave(interaction: discord.Interaction) -> None:
    voice_client = (
        interaction.guild.voice_client
        if interaction.guild is not None
        else None
    )

    if voice_client is None:
        await interaction.response.send_message("I'm not in a voice channel.")
        return

    try:
        if isinstance(voice_client, wavelink.Player):
            await voice_client.stop()
            await voice_client.disconnect()
        else:
            await voice_client.disconnect()
        await interaction.response.send_message("👋 Left the voice channel.")
    except (discord.ClientException, wavelink.WavelinkException) as exc:
        await interaction.response.send_message(
            f"❌ I couldn't leave the voice channel: {exc}"
        )


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not set. Put your bot token in .env or your environment."
    )

bot.run(TOKEN)
