# Stream React Native - credentials, token, and seed data

Run this once per session for tracks A, B, and D, right after intent classification and before the Project signals probe. Track C does not need credentials.

## Goal

Collect the Stream API key, user id, user token, and optional seed channels before touching code so the app can connect to real Chat data on first run.

This flow uses the **`stream`** CLI (binary name `stream`). It is the same CLI used by [`../stream-cli`](../stream-cli/SKILL.md). If the CLI is missing, use [`../stream-cli/bootstrap.md`](../stream-cli/bootstrap.md) for the install flow.

## Single upfront question (ask exactly once, then act immediately)

Post one message asking all relevant things together. Do not split into multiple rounds:

> To wire Chat RN with real data, I need a few quick answers:
>
> 1. **Credentials** - Should I fetch your API key via the Stream CLI and generate a token, or will you paste them yourself?
> 2. **User** - What user id and display name should the app connect as?
> 3. **Token expiry** - If I am generating the token: should it expire? (for example `1h`, `1d`, `30m`) or never expire?
> 4. **Seed channels** - Should I pre-create a few messaging channels with random usernames so the channel list has data immediately?
>
> If you want to handle credentials yourself, paste your API key and token and tell me whether to seed channels.

## After the user replies - act without further prompting

Once the user answers, execute the needed CLI steps in sequence without pausing between them. Narrate each step briefly, but do not ask "shall I continue?" between steps. Channel seeding is mutating; the user's upfront "yes" covers those seed calls.

### Step A0 - Confirm CLI install and auth

Detect the binary:

```bash
command -v stream
```

If `stream` does not resolve, follow [`../stream-cli/bootstrap.md`](../stream-cli/bootstrap.md). Ask for explicit approval before installing. Do not continue until `command -v stream` resolves, unless the user chooses to paste API key and token manually.

Verify auth with a cheap read:

```bash
stream --safe api OrganizationRead
```

- Exit 0 -> authenticated, proceed.
- Exit 2 -> run `stream auth login` as its own terminal invocation, per [`../stream/RULES.md`](../stream/RULES.md) > CLI safety.
- Exit 4 -> run `stream api --refresh`, then retry.
- Other exit -> report the error and fall back to pasted credentials.

### Step A - API key

If the user wants CLI-based credentials, read the configured app:

```bash
stream --safe api GetApp
```

Extract the `api_key` field and hold it in context. If the wrong app is selected, list apps or set the default using the Stream CLI flow from `stream-cli`; then re-run `GetApp`.

If the user pastes an API key, hold it in context and skip this step.

### Step B - Token

Generate a token for the chosen user id. `stream token` accepts a duration string; omit `--ttl` for a never-expiring local dev token.

```bash
# Never-expiring local dev token
stream token <user_id>

# Expiring token
stream token <user_id> --ttl 1h
```

Hold the token in context for code edits. Do not print it in summaries.

If the user pastes a token, hold it in context and skip generation.

### Step C - Seed channels (only if the user said yes)

Create 3 to 5 channels with realistic usernames. Use `messaging` as the channel type. The connected user must be a member of at least one seeded channel, or `ChannelList` will render empty.

These calls are mutating. Announce briefly:

> Seeding channels with mutating Stream API calls now.

#### C1 - Create user records

User records must exist before channel membership can be added. Create the token user and seed users in one `UpdateUsers` batch:

```bash
stream api UpdateUsers --body '{"users":{"<token_user_id>":{"id":"<token_user_id>","name":"Token User"},"alice":{"id":"alice","name":"Alice"},"bob":{"id":"bob","name":"Bob"},"carol":{"id":"carol","name":"Carol"}}}'
```

Use the user's chosen display name for `<token_user_id>`.

#### C2 - Create each channel with members

Use `GetOrCreateChannel`. Put membership in `data.members` as objects with `user_id`.

```bash
stream api GetOrCreateChannel type=messaging id=general --body '{"data":{"name":"General","created_by_id":"<token_user_id>","members":[{"user_id":"<token_user_id>"},{"user_id":"alice"},{"user_id":"bob"}]}}'
```

Generate short channel ids such as `general`, `random`, `team-alpha`. Make sure the token user appears in `data.members`.

After seeding, summarize without secrets:

> Created channels: `general` (<token_user_id>, alice, bob), `random` (<token_user_id>, carol), `team-alpha` (<token_user_id>, alice)

### Step D - Proceed automatically

After credentials and optional seeding succeed, return to [`SKILL.md`](SKILL.md) -> Project signals, then continue into [`builder.md`](builder.md). No additional prompt is needed.

If any CLI step fails and cannot be recovered, ask the user to paste the missing API key or token manually before editing code.

## What NOT to do

- Never put the API secret in app code, Expo config, native files, or chat.
- Never invent credentials.
- Never ask "should I continue?" between Step A, B, C, and D after the upfront answers.
- Never use `CreateChannel`; use `GetOrCreateChannel`.
- Never use `CreateUser`; use `UpdateUsers`.
- Never assume `created_by_id` adds a member. Membership must be set through `data.members`.
- Never pass bare user id strings as channel members. Use `[{"user_id":"alice"}]`.
- Never put channel members at the top level of the `GetOrCreateChannel` body.
