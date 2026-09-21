# Eli-Mini Architecture

## Document Authority

This is the authoritative record of Eli-Mini's established architecture.

`agent-files/Agents_Context.md` is the short-term working context for discoveries, proposals, unresolved questions, and implementation notes. It is not authoritative.

A decision belongs here when it defines a system boundary, durable behavior, deployment model, source of truth, or other architectural constraint that has been explicitly established. Lower-level implementation details remain in working context and code until needed.

## 1. Project Identity

Eli-Mini is a private Discord bot system for a small friend group.

The target system has two primary runtime layers:

1. **Python Discord Bot**
   - Discord commands and events
   - Discord-facing interaction
   - Voice-channel participation
   - Voice listening
   - Music playback orchestration
   - User-facing verification/confirmation

2. **TypeScript/Node.js Backend**
   - API
   - persistent state
   - PostgreSQL access
   - scheduling
   - backend processing
   - shared state across bot instances
   - server-side services

The system should remain proportional to a private deployment rather than being designed as a public SaaS platform.

## 2. Runtime Boundary

The Python process owns Discord-facing behavior.

The Node process owns persistent and shared backend concerns.

They communicate through an authenticated API/interface.

This separation prevents long-lived state and services from depending on the lifetime of a Discord bot process.

The physical repository boundary is flexible. The backend may eventually be in the same repository if that is cleaner, but the logical Python/Node responsibility boundary remains.

## 3. Production Hosting

The initial production target is an **Oracle Cloud Always Free Linux VM**.

The purpose is to eliminate dependence on a friend's personal computer being online 24/7.

The initial deployment may run the Node backend and PostgreSQL on the same VM because the current workload is small.

Oracle is a deployment target, not an application-domain dependency. The application should remain portable to another Linux host.

## 4. Database and Source of Truth

**PostgreSQL is the durable source of truth for backend state.**

It must retain state that needs to survive process or deployment restarts.

Expected domains include:

- Discord user/guild/channel references
- bot instances
- reminders
- temporary voice-channel records
- Media Group metadata and authorization state
- Watch Session records
- playback positions
- other durable backend state

The exact schema, migrations, ORM/query layer, and indexes are implementation decisions.

## 5. Python Discord Bot

The Python bot owns:

- Discord commands
- Discord events
- joining/leaving/moving between voice channels
- voice interaction
- music playback orchestration
- voice-request verification messages
- administrator confirmation
- requests to backend services

The bot must not become the authoritative store for long-lived application state.

## 6. Node.js Backend

The Node backend owns:

- authenticated API endpoints
- PostgreSQL access
- durable state
- scheduling
- temporary-VC lifecycle state
- Media Group state
- Watch Session persistence
- backend processing
- bot registration/management
- shared state across bot instances

The backend does not replace Discord as the source of truth for Discord-native objects.

## 7. Identity and Authentication

Discord's identity system is the primary identity layer for Discord users.

Persistent references should use Discord identifiers where applicable rather than introducing a redundant general user-account system.

Python bot ↔ Node backend communication must be authenticated.

Custom credentials are separate from Discord identity. Media Group credentials are one such custom credential.

The exact API authentication mechanism and custom-credential cryptography are not yet finalized.

## 8. JOIN CALL / Persistent Voice Listening

`/join <channel>` joins the requested Discord voice channel.

The target may be a normal or temporary voice channel. If the bot is already elsewhere, it can move to the requested channel.

Joining establishes the intended persistent listening mode.

While connected, the bot should listen for the configured wake/keyword mechanism and process relevant speech as potential prompts.

Listening is a distinct capability from music playback and must remain possible while music is playing.

The wake word, speech-to-text system, speaker identification, overlap handling, and retention rules remain open implementation decisions.

## 9. Music Request Architecture

Music requests use a common normalized pipeline regardless of input source.

Supported input categories are intended to include:

- Spotify song links
- Spotify playlist links
- Spotify artist links
- YouTube links
- other supported audio links
- text searches
- verified voice requests

Provider-specific resolution and playback should be isolated from the normalized request model.

### Voice Verification Flow

Voice requests are not automatically authoritative.

```
Voice
  ↓
Capture / speech processing
  ↓
Candidate prompt
  ↓
Discord verification message
  ↓
Administrator may edit
  ↓
Confirmation command
  ↓
Current edited message contents
  ↓
Normal music-request pipeline
```

The verification step exists because transcription can be wrong and multiple users can speak simultaneously.

The exact command name, permissions, transcription provider, wake-word mechanism, queue behavior, and Spotify-to-playable-audio resolution remain to be finalized.

## 10. Ping / Backend Connectivity

The project includes a backend connectivity test.

It must test bot → Node server communication rather than only replying locally in Discord.

The diagnostic model should distinguish:

- Discord bot functioning
- backend reachable
- backend authentication/configuration failure
- backend unavailable

The exact response is an implementation detail.

## 11. Durable Reminder System

Reminders are year-round and persistent.

They support arbitrary future durations, including very short and very long periods.

A reminder can contain descriptive content and optionally an image.

Delivery can be a Discord DM and/or an optional server-based mechanism.

Reminder records are stored in PostgreSQL.

Scheduling uses persisted timestamps/state, not a process that sleeps for the entire duration. After a restart, the scheduler recovers pending reminders from the database.

Calendar semantics for months/years, timezone behavior, recurring reminders, edit/cancel behavior, and exact server-delivery semantics remain open.

## 12. Temporary Voice Channels

Eli-Mini can create temporary Discord voice channels through Discord's supported channel-management APIs.

Creation accepts configuration including a requested lifetime.

Lifecycle state must be persisted sufficiently for recovery after restarts.

Expiration results in cleanup according to the final lifecycle rules.

The behavior when users remain inside at expiration is unresolved.

## 13. Media Groups

A Media Group is a private, credential-gated media space for friends.

Creation generates an encoded-character credential. The original credential is the access secret.

Protected operations include, at minimum:

- uploading
- deleting
- managing

Supported media is intended to include:

- images
- audio
- video
- text files

PostgreSQL stores metadata and authorization state. Large binary media should use file/object storage rather than relational rows.

Discord identity and Media Group credentials remain separate.

The exact credential format, length, hashing/encryption, recovery/rotation, authorization model, and file-storage provider remain open.

## 14. Watch Sessions

A Watch Session allows the bot to join a voice channel and stream selected media, initially intended for anime.

Each session receives a session ID.

Persist at minimum:

- session ID
- show
- episode
- exact playback timestamp

`/resume-session <session-id>` restores the saved episode and timestamp.

When an episode ends, the system should advance to the next episode.

Opening/intros and ending/outros should be skipped automatically whenever technically possible.

The media provider is intentionally abstracted from session state. Provider choice, authentication, stream acquisition, intro/outro detection, session access, and unavailable-source behavior remain open.

## 15. Multi-Bot Model

The backend should support multiple Eli-Mini bot instances.

A future conceptual target of approximately 100 bots has been discussed, but current usage is a small friend group.

This does not justify distributed infrastructure by itself. Start with one centralized Node service and PostgreSQL database; scale only when actual requirements demand it.

Each bot instance must authenticate to the backend and have a clear identity/configuration.

## 16. Storage

PostgreSQL is for structured durable state.

Large binary media should use file/object storage.

The initial Oracle VM may host both application and database services. The architecture should permit later separation.

Backups are independent of hosting and must be treated as a recovery requirement.

## 17. Security and Private Configuration

The shared repository must not contain private instance credentials.

Never commit:

- Discord bot tokens
- database passwords
- API secrets
- provider credentials
- cookies
- encryption keys
- private storage credentials
- instance-specific deployment secrets

Secrets must be supplied through the deployment environment or another appropriate secret mechanism.

## 18. Architecture Change Rule

```
Requirement / discovery
        ↓
Agents_Context.md
        ↓
Investigation / implementation
        ↓
Validation
        ↓
Explicit approval
        ↓
ARCHITECTURE.md
```

Architectural changes must be deliberate. Do not let implementation convenience silently redefine the system.

When a decision changes, update both documents so the architecture reflects the new decision and working context no longer presents obsolete information as current.

## 19. Required Boundaries

The following boundaries should remain explicit:

- Discord identity vs custom credentials
- Python Discord behavior vs Node backend behavior
- transient process state vs PostgreSQL durable state
- relational metadata vs binary media storage
- normalized music requests vs provider-specific playback
- Watch Session state vs external media provider
- development machine vs production server
- public code/configuration vs private secrets

These boundaries are intended to keep the system maintainable and replaceable without prematurely splitting it into unnecessary services.

## 20. Current Architectural Status

Established direction:

- Python Discord bot
- TypeScript/Node.js backend
- PostgreSQL
- Oracle Cloud Always Free Linux VM
- authenticated bot-to-backend communication
- durable backend state
- persistent reminders
- temporary voice channels
- Media Groups
- Watch Sessions
- unified music-request handling
- persistent voice listening
- Discord as the primary identity layer
- separation of custom credentials from Discord identity

Provider-specific and lower-level decisions remain in `Agents_Context.md` until investigated and explicitly approved.
