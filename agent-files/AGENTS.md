# Eli-Mini Agent Rules

## 1. Purpose

Eli-Mini is a private Discord bot system with a Python Discord runtime and a TypeScript/Node.js backend. These rules define how agents should inspect, modify, and document the project.

Before making meaningful changes, read:

1. `agent-files/Agents_Context.md`
2. `agent-files/ARCHITECTURE.md`
3. Relevant project/framework documentation
4. The current implementation being changed

Do not treat a proposal, TODO, discussion, or open question as implemented.

## 2. Document Authority

- `ARCHITECTURE.md` is the authoritative record of established architectural decisions.
- `Agents_Context.md` is the working record for discoveries, current work, proposals, unresolved questions, and temporary implementation context.
- This file defines agent behavior and does not replace either document.
- Avoid duplicating architecture in `Agents_Context.md`; keep only context that is useful for active work.

## 3. Architecture Change Rule

For a meaningful architectural change:

1. Record the requirement, discovery, or proposal in `Agents_Context.md`.
2. Investigate or prototype it.
3. Validate the result against the actual implementation and requirements.
4. Obtain explicit approval for the architectural decision.
5. Put the finalized decision in `ARCHITECTURE.md`.
6. Remove or update stale working-context notes.

Do not silently turn an implementation convenience into an architectural requirement.

## 4. System Boundaries

The intended logical runtime boundary is:

- **Python Discord bot:** Discord commands/events, voice interaction, Discord-facing music behavior, and user-facing verification.
- **TypeScript/Node.js backend:** API, persistent state, PostgreSQL, scheduling, backend processing, shared bot state, and server-side services.

The physical repository boundary may change if a same-repository backend proves cleaner. Repository layout must not blur the logical runtime responsibilities.

The initial production target is an Oracle Cloud Always Free Linux VM. Do not make Oracle-specific services a core application dependency unless explicitly approved.

## 5. Implementation Rules

- Inspect current code before proposing rewrites.
- Prefer small, testable changes.
- Keep Discord-specific code separate from backend/domain code.
- Use provider interfaces/adapters where an external provider has not been finalized.
- Durable state belongs in persistent storage; do not rely on process memory for state that must survive restarts.
- Long-duration reminders must be represented as persisted timestamps/state, not one long sleep.
- Keep large binary media out of PostgreSQL unless a specific case requires otherwise.
- Never hard-code secrets.
- Do not assume the current monolithic `bot.py` is the final architecture.

## 6. Voice and Music Rules

Voice listening and music playback are separate concerns and must be able to coexist.

Voice music requests must use the verification flow established in the architecture. Do not remove administrator confirmation simply to simplify implementation.

Music-provider details must remain isolated from the normalized request model.

## 7. Identity and Security

Discord is the primary identity layer for Discord users. Use Discord IDs for persistent references rather than creating an unnecessary second user-account system.

Custom credentials, such as Media Group access credentials, are separate from Discord identity. Their cryptographic design is not finalized and must not be invented without approval.

Never commit or unnecessarily log tokens, passwords, cookies, database credentials, provider credentials, encryption keys, or private instance configuration.

## 8. Change Discipline

Do not modify unrelated code.

Do not push, merge, delete, or rewrite branches unless explicitly requested.

When a change affects architecture, document the boundary and decision in the appropriate agent file.

When requirements are ambiguous, record the ambiguity in `Agents_Context.md` rather than silently choosing behavior with long-term consequences.

## 9. Review Standard

Before considering a substantial architectural or implementation change complete, check for:

- duplicated responsibilities
- conflicting sources of truth
- in-memory-only durable state
- provider-specific assumptions leaking into domain logic
- secrets entering source control
- unnecessary Python/Node coupling
- unnecessary Discord/provider coupling
- restart/recovery failures
- assumptions that a developer's computer is always online

The system is for a private friend group. Avoid public-platform complexity unless an actual requirement justifies it.
