import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")


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


if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN is not set. Put your bot token in .env or your environment."
    )

bot.run(TOKEN)
