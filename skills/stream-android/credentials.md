# Stream Android - credentials, token, and seed data

Run this **once per session** for tracks A, B, and D, right after intent classification and before the Project signals probe. Track C (reference lookup) does not need this — return to [`SKILL.md`](SKILL.md) instead.

## Goal

Collect the Stream **API key**, a **user token**, and optionally seed a few channels — all before touching code — so the app has real data to show from the first run.

This skill uses the **`stream`** CLI (binary name `stream`, installed from `https://getstream.io/cli/install.sh`). It is the same binary used by [`skills/stream`](../stream/SKILL.md). Do **not** confuse it with the `stream-cli` binary from `GetStream/stream-cli` on GitHub — the command surface is different.

## Single upfront question (ask exactly once, then act immediately)

Post **one message** asking all three things together. Do not split into multiple rounds:

> To wire everything up with real data, I need a few quick answers:
>
> 1. **Credentials** — Should I fetch your API key via the Stream CLI and generate a token, or will you paste them yourself?
> 2. **Token expiry** — If I'm generating the token: should it expire? (e.g. `1h`, `1d`, `30m`) or never expire?
> 3. **Seed channels** — Should I pre-create a few channels with random usernames so the app has something to show immediately?
>
> If you want to handle everything yourself, just paste your API key and token and tell me whether to seed channels.

## After the user replies — act without further prompting

Once the user answers, execute all CLI steps in sequence **without pausing for confirmation between them**. Narrate each step briefly as you go (one line per action), but do not stop to ask "shall I continue?". Channel seeding is mutating; the user's "yes" upfront covers the consent for those calls.

### Step A0 — Confirm CLI install and auth (preflight, mandatory)

The binary is named **`stream`**. Detect it before any other CLI step:

```bash
command -v stream
```

If `stream` does not resolve, install it after explicit user approval:

```bash
/bin/bash -c "$(curl -fsSL https://getstream.io/cli/install.sh)"
```

For a deeper description of what `install.sh` does (per-step breakdown, checksum verification, audit recipe), see [`skills/stream/bootstrap.md`](../stream/bootstrap.md). Do not proceed until `command -v stream` resolves.

Once installed, verify the user is authenticated with a cheap probe:

```bash
stream --safe api OrganizationRead
```

- Exit `0` → authenticated, proceed to Step A.
- Exit `2` → not authenticated. Tell the user to run `stream auth login` in a terminal where a browser window can open (PKCE flow), then re-run the probe before continuing.
- Other exit codes → report the error and stop.

### Step A — API key

```bash
stream --safe api GetApp
```

`GetApp` auto-resolves the org and app from the CLI's saved config. Extract the `api_key` field from the JSON response and hold it in context.

If the user has multiple apps configured and the wrong one is selected, set the default first:

```bash
stream config set app <app_id>
```

…then re-run `stream --safe api GetApp`.

### Step B — Token

`stream token` accepts a TTL as a duration string (`30s`, `2h`, `1d`); no need to compute an epoch. Omit `--ttl` for a never-expiring token.

```bash
# Never-expiring
stream token <user_id>

# Expiring (use the user's requested duration verbatim, e.g. 1h, 30m, 1d)
stream token <user_id> --ttl 1h
```

Hold the token in context. Use it (and the API key from Step A) in every code snippet — no placeholder strings.

### Step C — Seed channels (only if the user said yes)

Create 3–5 channels with random realistic usernames. Use `messaging` as the channel type. The token user **must** end up as a member of at least one channel — otherwise the channel list will render empty on first launch even though the seed succeeded.

These calls are mutating. Run them without `--safe` (the user's upfront "yes" covers the consent). Announce briefly: *"Seeding channels (mutating operations)…"* before the first call.

For each channel:

```bash
# 1. Create (or fetch) the channel — token user is the creator and an automatic member
stream api GetOrCreateChannel type=messaging id=<channel-id> --body '{"data":{"name":"<display name>","created_by_id":"<token_user_id>"}}'

# 2. Add additional members
stream api UpdateChannel type=messaging id=<channel-id> --body '{"add_members":["<user1>","<user2>"]}'
```

Generate short memorable channel IDs (e.g. `general`, `random`, `team-alpha`) and a small set of random usernames (e.g. `alice`, `bob`, `carol`, `dave`, `eve`). Easiest pattern: pass the **token user id** as `created_by_id` (they become the creator and an automatic member), then `UpdateChannel` to add the others.

If a call fails with a parameter error, fall back to `stream --safe api GetOrCreateChannel --help` (or `UpdateChannel --help`) to confirm the exact signature, then retry.

After seeding, print a brief summary:

> Created channels: `general` (<token_user_id>, alice, bob), `random` (<token_user_id>, carol, dave), `team-alpha` (<token_user_id>, alice, eve)

### Step D — Proceed automatically

After all CLI steps succeed, return to [`SKILL.md`](SKILL.md) → **Project signals**, then continue into [`builder.md`](builder.md) — no additional prompt needed. If any CLI step fails, explain the error briefly and ask the user to paste the missing value manually before continuing.

## What NOT to do

- Never put the API **secret** in app code — the CLI uses it server-side only.
- Never invent or fabricate credentials.
- Never ask "should I continue?" between Step A, B, C, and D — execute the whole sequence once the user's upfront answers are in.
- Never use `stream-cli` (the public Go CLI from `GetStream/stream-cli`) commands here — that is a different binary with a different command surface (`stream-cli chat get-app`, `stream-cli chat create-token`, etc.). This skill targets the `stream` binary only.
- Never run `CreateChannel` — the correct endpoint is `GetOrCreateChannel`. Same for users (`UpdateUsers`, not `CreateUser`) and calls (`GetOrCreateCall`, not `CreateCall`).
