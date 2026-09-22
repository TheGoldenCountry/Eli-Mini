# Eli-Mini — Agents Context

## Purpose

This is the shared working context for Bryan, collaborators, ChatGPT, Codex, and other agents.

It is intentionally a living document. It may contain implementation findings, proposals, unresolved questions, and review notes. It is **not** the authoritative architecture record; established architecture belongs in `agent-files/ARCHITECTURE.md`.

## Current Project

Eli-Mini is a private Discord bot for Bryan, his friend, and their friend group. The intended system is larger than the current prototype and combines a Python Discord bot with a TypeScript/Node.js backend and PostgreSQL.

The project is not being designed as a public SaaS platform. The architecture should therefore stay simple and proportional to a small private deployment while still supporting multiple bot instances later.

## Current Repository State

The repository is currently primarily a Python `discord.py` bot and is more monolithic than the intended architecture.

Known current characteristics:

- `bot.py` contains the main bot and command behavior.
- Current commands include `/ping`, `/hello`, `/about`, `/join`, `/play`, and `/leave`.
- Voice connection/playback logic is currently in the bot implementation through Wavelink.
- YouTube playback uses a local Lavalink 4.2.2 node with the youtube-source 1.18.2 plugin; the Python bot no longer runs yt-dlp/FFmpeg directly and does not depend on a YouTube proxy or browser-cookie export.
- Wavelink 3.5.2 is used as the Python Lavalink client and includes Discord DAVE support.
- The development container uses Python 3.12 Bookworm, Node 22, and Java 21. Chromium and local FFmpeg are no longer required for YouTube playback.
- `reminders.py` currently provides a durable local SQLite reminder/alarm scheduler. The long-term architecture still intends for reminders to move to PostgreSQL behind the Node backend.
- There is not yet an established Node API, Media Group subsystem, or Watch Session subsystem.

The existing implementation is evidence about what exists today, not a constraint on the target architecture.

## Hosting Decision

**Initial production target: Oracle Cloud Always Free Linux VM.**

The reason is operational simplicity for this project: the backend should not depend on a friend's personal computer being powered on 24/7.

The initial deployment can run the Node backend and PostgreSQL on the same VM because the expected workload and storage needs are small.

Oracle is a hosting target, not an application dependency. The backend should remain portable to another Linux host later.

Backups remain necessary even with Oracle. Hosting and backup are separate concerns.

## Backend Direction

The backend will be TypeScript running on Node.js.

It is intended to own:

- authenticated API endpoints
- PostgreSQL access
- durable application state
- reminder scheduling
- temporary-VC lifecycle state
- Media Group metadata
- Watch Session persistence
- backend processing
- bot registration/management
- shared state for multiple bot instances

The Python bot remains the Discord-facing runtime.

The exact Node framework, API protocol, API authentication mechanism, and database access layer are not yet finalized.

## Database Direction

PostgreSQL is the durable source of truth.

Expected data domains include:

- Discord user/guild/channel references
- bot instances
- reminders
- temporary voice-channel records
- Media Group metadata and authorization state
- Watch Session records
- saved playback positions
- other durable backend state

Exact schema, migrations, ORM/query layer, indexes, and retention rules remain implementation decisions.

## Feature Requirements

### 1. JOIN CALL

`/join <channel>` should join the specified Discord voice channel, including temporary channels.

If the bot is already elsewhere, it should be able to move to the requested channel.

Joining is also intended to activate continuous listening. While connected, the bot should listen for a configured keyword/wake mechanism and process relevant speech as possible prompts.

This is therefore a persistent voice-interaction state, not merely a music join command.

Still open:

- wake word/keyword
- speech-to-text provider
- where speech processing occurs
- speaker identification
- overlapping-speech handling
- voice retention/privacy behavior

### 2. PLAY SONG-LINK-AUDIO

The system should accept, where supported:

- Spotify song links
- Spotify playlist links
- Spotify artist links
- YouTube links
- other compatible audio links
- text searches
- voice requests

All inputs should enter a common normalized music-request pipeline.

Voice requests require verification because transcription can be wrong and users may talk over each other:

1. Capture speech.
2. Interpret it as a candidate music prompt.
3. Post the interpreted prompt in Discord.
4. Allow an administrator to edit the message if necessary.
5. An administrator confirms it with a command such as `/confirm-prompt`.
6. Use the **current edited message contents** as the authoritative prompt.
7. Send that prompt through the normal music pipeline.

The bot should continue listening while music is playing.

Provider-specific resolution/playback must be separated from the normalized request model.

Still open:

- Spotify-to-playable-audio resolution
- initial provider set
- exact search strategy
- transcription/wake-word implementation
- queue/concurrency behavior
- administrator permission rules
- exact confirmation command

### 3. PING-TEST

The project needs a backend connectivity test that verifies bot → Node server communication.

It should conceptually distinguish:

- Discord bot working
- backend reachable
- backend authentication/configuration failure
- backend unavailable

The exact command output is not finalized.

### 4. TIMER-REMINDER-YEAR_ROUND

Reminders must persist year-round and survive process restarts.

They should support arbitrary future durations, including examples such as 5 minutes, 30 minutes, 5 months, and 30 years.

A reminder may contain descriptive content and optionally an image.

Delivery may be:

- DM to the user
- optional server-based reminder

Reminders must be stored in PostgreSQL. The scheduler must use persisted timestamps rather than sleeping for the entire duration, and it must recover outstanding reminders after restart.

Still open:

- command syntax
- month/year calendar semantics
- timezone rules
- recurring reminders
- edit/cancel behavior
- exact server reminder/pinning behavior

### 5. TEMP-VC

The bot should create temporary Discord voice channels using Discord's supported APIs.

Creation accepts configuration including a requested lifetime/age.

Temporary-channel state must be persisted sufficiently for lifecycle recovery after restarts.

Still open: what happens when the expiration time is reached while users are still inside.

### 6. MEDIA-GROUP

A Media Group is a private friend-group media space.

Creation generates an encoded-character credential. The original credential is the access secret.

Users with the appropriate credential can perform protected operations such as:

- upload
- delete
- manage

Supported media is intended to include:

- images
- audio
- video
- text files

PostgreSQL should store metadata and authorization state. Large binary media should use file/object storage rather than relational rows.

Discord identity remains the primary identity layer. Media Group credentials are a separate access mechanism.

Still open:

- credential length/format
- hashing/encryption approach
- credential rotation/recovery
- detailed authorization rules
- file-storage provider
- upload size/retention limits

### 7. WATCH-SESSIONS

A Watch Session lets the bot join a voice channel and stream selected media; the initial target is anime.

Each session gets a session ID.

When a session is left or otherwise saved, persist:

- session ID
- show
- episode
- exact playback timestamp

`/resume-session <session-id>` restores the saved episode and timestamp.

When an episode ends, advance automatically to the next episode.

Skip opening/intros and ending/outros automatically whenever technically possible.

The provider is intentionally undecided. Candidate approaches discussed include an authorized Crunchyroll account and other providers. The session state model must remain provider-independent.

Still open:

- provider
- provider authentication
- stream acquisition
- intro/outro detection
- session ownership/access
- concurrent sessions
- behavior when a saved source becomes unavailable

### 8. NODE SERVER

The Node backend is the shared service layer and should be capable of supporting multiple Eli-Mini bot instances.

A rough future target of about 100 bots has been discussed, but the current deployment is only a small friend group. Do not introduce distributed infrastructure solely for the theoretical target.

The server centralizes:

- security/authentication
- persistent state
- database access
- bot registration/management
- reminders
- backend processing
- shared state
- APIs used by Python bot instances

It may ultimately live in the same repository as the bot if that is cleaner. Private instance-specific configuration must remain private regardless of repository layout.

## Identity and Security Direction

Discord already provides user identity. Use Discord user/guild/channel IDs as canonical references where the backend needs to associate persistent records.

Do not create a general duplicate user-account system without a concrete requirement.

Custom credentials, especially Media Group credentials, are separate from Discord identity.

Do not commit:

- Discord tokens
- database credentials
- API secrets
- provider credentials
- cookies
- encryption keys
- private storage credentials
- instance-specific deployment data

The cryptographic design of custom credentials is intentionally deferred.

## Data and Storage Direction

PostgreSQL stores structured durable state.

Binary media should use appropriate file/object storage.

The Oracle VM may initially host both Node and PostgreSQL. The architecture should allow later separation without changing domain responsibilities.

Backups should be automated and recoverable; the free hosting tier is not itself a backup strategy.

## Review / Open Questions

1. Wake word and speech pipeline?
2. Speaker identification and overlapping speech?
3. Initial music providers and Spotify resolution?
4. Node framework and API protocol?
5. Bot-to-backend authentication?
6. Database access layer and migrations?
7. Reminder calendar/timezone semantics?
8. Temporary-VC expiration behavior with occupants?
9. Media Group credential and cryptographic design?
10. Media file storage provider and limits?
11. Watch-session provider and authentication?
12. Intro/outro detection method?
13. Same repository or separate backend repository?
14. Oracle VM monitoring, deployment, and backup procedure?

These are intentionally open. Do not guess them into the architecture.

## Maintenance

When an open question is resolved:

1. Decide whether it affects architecture or only implementation.
2. For architectural decisions, obtain explicit approval and update `ARCHITECTURE.md`.
3. Remove/update the corresponding item here.
4. Do not leave obsolete proposals presented as current.

Keep this document consolidated rather than appending repetitive history.
