import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import discord

TIME_UNITS: dict[str, int] = {
    "hours": 60 * 60,
    "days": 24 * 60 * 60,
    "weeks": 7 * 24 * 60 * 60,
    "years": 365 * 24 * 60 * 60,
}

KIND_LABELS = {
    "reminder": "Reminder",
    "alarm": "Alarm",
}


class ReminderManager:
    """Persist and deliver one-shot reminders and alarms."""

    def __init__(self, db_path: str = "reminders.db") -> None:
        self.db_path = Path(db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('reminder', 'alarm')),
                    fire_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_fire_at "
                "ON reminders (fire_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_reminders_user_id "
                "ON reminders (user_id)"
            )

    def create(
        self,
        user_id: int,
        name: str,
        amount: int,
        unit: str,
        kind: str,
    ) -> tuple[int, datetime]:
        if unit not in TIME_UNITS:
            raise ValueError("Unsupported time unit.")
        if kind not in KIND_LABELS:
            raise ValueError("Unsupported reminder type.")
        if amount < 1:
            raise ValueError("Amount must be at least 1.")

        fire_at = datetime.now(timezone.utc) + timedelta(
            seconds=amount * TIME_UNITS[unit]
        )

        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO reminders (user_id, name, kind, fire_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    user_id,
                    name,
                    kind,
                    fire_at.isoformat(),
                ),
            )
            reminder_id = int(cursor.lastrowid)

        return reminder_id, fire_at

    def get_user_reminders(
        self,
        user_id: int,
        limit: int = 25,
    ) -> list[sqlite3.Row]:
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT id, user_id, name, kind, fire_at
                FROM reminders
                WHERE user_id = ?
                ORDER BY fire_at ASC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

    def cancel(self, reminder_id: int, user_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM reminders
                WHERE id = ? AND user_id = ?
                """,
                (reminder_id, user_id),
            )
            return cursor.rowcount > 0

    def get_due(self, now: datetime | None = None) -> list[sqlite3.Row]:
        current = now or datetime.now(timezone.utc)
        with self._connect() as connection:
            return connection.execute(
                """
                SELECT id, user_id, name, kind, fire_at
                FROM reminders
                WHERE fire_at <= ?
                ORDER BY fire_at ASC
                """,
                (current.isoformat(),),
            ).fetchall()

    def delete(self, reminder_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM reminders WHERE id = ?",
                (reminder_id,),
            )


def format_timestamp(fire_at: str) -> str:
    """Format an ISO UTC timestamp as a Discord relative-time tag."""
    try:
        timestamp = datetime.fromisoformat(fire_at).astimezone(timezone.utc)
    except ValueError:
        return fire_at

    return f"<t:{int(timestamp.timestamp())}:R>"


async def deliver_due_reminder(
    bot: discord.Client,
    reminder: sqlite3.Row,
) -> bool:
    """DM one due item. Returns True when the row should be removed."""
    user_id = int(reminder["user_id"])
    name = str(reminder["name"])
    kind = str(reminder["kind"])

    try:
        user = await bot.fetch_user(user_id)
        label = KIND_LABELS.get(kind, "Reminder")

        if kind == "alarm":
            message = (
                f"🚨 **{label}: {name}**\n"
                "It's time! Your alarm is going off.\n"
                "📞 I can't start a one-to-one Discord voice call from a bot, "
                "so open this DM and start the call from Discord."
            )
        else:
            message = f"⏰ **{label}: {name}**"

        await user.send(message)
    except (discord.Forbidden, discord.NotFound) as exc:
        print(
            f"Could not DM reminder {reminder['id']} to user {user_id}: {exc}"
        )
    except discord.HTTPException as exc:
        print(
            f"Discord returned an HTTP error delivering reminder "
            f"{reminder['id']} to user {user_id}: {exc}"
        )

    return True


async def reminder_scheduler(
    bot: discord.Client,
    manager: ReminderManager,
    interval_seconds: int = 5,
) -> None:
    """Continuously deliver due reminders while the bot is running."""
    while not bot.is_closed():
        try:
            due = await asyncio.to_thread(manager.get_due)

            for reminder in due:
                should_delete = await deliver_due_reminder(bot, reminder)
                if should_delete:
                    await asyncio.to_thread(
                        manager.delete,
                        int(reminder["id"]),
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Reminder scheduler error: {exc}")

        await asyncio.sleep(interval_seconds)
