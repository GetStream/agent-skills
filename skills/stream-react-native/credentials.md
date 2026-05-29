# Stream React Native - credentials, token, and demo data

Run this once per session for tracks A, B, and D before writing connected Chat or Video code or creating requested demo data. Track C does not need credentials.

## Goal

Collect the Stream API key, user id, and user token so the app can connect to real Stream data on first run. The API key + token flow is identical for Chat and Video.

- **Chat** can also seed optional **demo data** (channels, users, messages) - see Step C.
- **Video** needs **no demo/seed data**: calls are ephemeral and created at runtime by `client.call(type, id)`, so skip Step C for Video-only sessions and confirm only the API key, user, and token.

For a brand-new app, scaffolding may happen before this file if the runtime or target directory must be resolved first.

This flow uses the **`stream`** CLI (binary name `stream`). It is the same CLI used by [`../stream-cli`](../stream-cli/SKILL.md). If the CLI is missing, use [`../stream-cli/bootstrap.md`](../stream-cli/bootstrap.md) for the install flow.

## Single upfront question (ask exactly once, then act immediately)

Post one message asking all relevant things together. Do not split into multiple rounds. Include question 4 (demo data) **only when Chat is in scope** - for Video-only sessions, drop it (calls need no seed data):

> To wire Stream with real data, I need a few quick answers:
>
> 1. **Credentials** - Should I fetch your API key via the Stream CLI and generate a token, or will you paste them yourself?
> 2. **User** - What user id and display name should the app connect as?
> 3. **Token expiry** - If I am generating the token: should it expire? (for example `1h`, `1d`, `30m`) or never expire?
> 4. **Demo data** *(Chat only)* - Do you want me to create demo channels? If you want more demo data, say whether to add demo users and messages too. (I will namespace every demo id under a per-session `demo-<random>-` prefix, and confirm with you before writing into a Stream app that already has real channels.)
>
> If you want to handle credentials yourself, paste your API key and token (and, for Chat, tell me whether to create demo data).

## After the user replies - act without further prompting

Once the user answers, execute the needed CLI steps in sequence without pausing between them. Narrate each step briefly, but do not ask "shall I continue?" between steps. Demo data calls are mutating; run them only when the user asked for them.

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

Extract the `api_key` field **and the app `name`** and hold both in context. If the wrong app is selected, list apps or set the default using the Stream CLI flow from `stream-cli`; then re-run `GetApp`.

If the user pastes an API key, hold it in context and skip this step.

**Echo the selected app to the user before any mutation:** before running Step C, say `Selected Stream app: "<app_name>" (api_key: <last_4_chars>)` so a misconfigured CLI default is caught before it writes to the wrong app. If the user expected a different app, stop and let them switch with `stream apps select` (or whichever app-switching flow `stream-cli` uses) before continuing.

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

### Step C - Demo data (Chat only, and only if the user asked)

Video needs no demo data - skip this step for Video-only sessions. For Chat, create 3 to 5 channels with realistic usernames. Use `messaging` as the channel type. The connected user must be a member of at least one demo channel, or `ChannelList` will render empty.

These calls are mutating. **All demo ids must be namespaced** so they cannot collide with real users or channels that already exist in the selected Stream app.

#### C0 - Pre-mutation safety check

Before running any `UpdateUsers` / `GetOrCreateChannel` / `SendMessage`:

1. **Generate a per-session demo prefix** and hold it in context. Default form: `demo-<short_random>-` where `<short_random>` is 4-6 lowercase chars (e.g., `demo-k3p9-`). Every demo user id, channel id, and seeded message custom field uses this prefix. Do not reuse a prefix across sessions - generate a fresh one each time so retries land in a fresh namespace.
2. **Detect whether the selected app already has real data.** Run `stream --safe api QueryChannels --body '{"filter_conditions":{"type":"messaging"},"limit":1}'` and check whether the response includes any channels that do **not** start with a `demo-` prefix.
3. **Confirm explicitly when the app is non-empty.** If real channels exist, surface the count and a sample channel id, and require the user to type a confirmation before continuing:
   > Selected Stream app `"<app_name>"` already has real channels (e.g., `<example_cid>`). I am about to create demo users and channels namespaced under `<demo_prefix>` so they cannot collide. Confirm with `seed demo` to proceed, or say `cancel`.
4. **Empty / dev app:** announce and proceed without explicit confirmation:
   > Selected Stream app `"<app_name>"` looks empty. Creating namespaced demo data under prefix `<demo_prefix>` now.

If the user cancels, stop Step C and return to Step D with credentials only.

Route demo data through [`../stream-cli/SKILL.md`](../stream-cli/SKILL.md) and [`../stream-cli/cli-cookbook.md`](../stream-cli/cli-cookbook.md). Keep the CLI safe-mode-first rule for endpoint discovery and only run mutating calls after the explicit demo-data request and the confirmation above.

#### C1 - Create namespaced user records

User records must exist before channel membership can be added. Apply the demo prefix to every demo user id (the **token user keeps its own id** - that is the user the app will connect as):

```bash
# <demo_prefix> e.g. demo-k3p9-
stream api UpdateUsers --body '{"users":{"<token_user_id>":{"id":"<token_user_id>","name":"<display_name>"},"<demo_prefix>alice":{"id":"<demo_prefix>alice","name":"Alice (demo)"},"<demo_prefix>bob":{"id":"<demo_prefix>bob","name":"Bob (demo)"},"<demo_prefix>carol":{"id":"<demo_prefix>carol","name":"Carol (demo)"}}}'
```

`UpdateUsers` is upsert - it is safe to re-run.

#### C2 - Create each channel with members (namespaced ids)

Use `GetOrCreateChannel`. Prefix every channel id with `<demo_prefix>` and tag the channel with a `seeded_by_skill: true` marker in `data.custom` so later runs can detect this skill's own seeded data:

```bash
stream api GetOrCreateChannel type=messaging id=<demo_prefix>general --body '{"data":{"name":"General (demo)","created_by_id":"<token_user_id>","members":[{"user_id":"<token_user_id>"},{"user_id":"<demo_prefix>alice"},{"user_id":"<demo_prefix>bob"}],"custom":{"seeded_by_skill":true,"demo_prefix":"<demo_prefix>"}}}'
```

Use namespaced channel ids such as `<demo_prefix>general`, `<demo_prefix>random`, `<demo_prefix>team-alpha`. Make sure the token user appears in `data.members`. `GetOrCreateChannel` is idempotent on the `(type, id)` pair - re-running with the same prefix returns the existing channel rather than duplicating it.

After creating demo channels, summarize without secrets and **without printing user tokens**:

> Created demo channels in `"<app_name>"`: `<demo_prefix>general` (<token_user_id>, <demo_prefix>alice, <demo_prefix>bob), `<demo_prefix>random` (<token_user_id>, <demo_prefix>carol), `<demo_prefix>team-alpha` (<token_user_id>, <demo_prefix>alice)

#### C3 - Send demo messages idempotently (only if the user asked for messages or more demo data)

Use `SendMessage` through the Stream CLI cookbook. Each message's `user_id` must belong to an existing user (so use the namespaced demo users from C1, or the token user). Tag every seeded message with a stable `custom.seed_key` so a re-run can detect and skip already-seeded messages.

Before sending, check whether the channel already contains a message with the same `seed_key`:

```bash
# Skip-if-present check (one query per (channel, seed_key)):
stream --safe api QueryChannels --body '{"filter_conditions":{"type":"messaging","cid":"messaging:<demo_prefix>general"},"messages_limit":50}'
# If the returned messages already include one whose custom.seed_key matches
# <seed_key>, skip the send for that key.
```

Then send only the missing messages:

```bash
stream api SendMessage type=messaging id=<demo_prefix>general --body '{"message":{"text":"Hello from Alice","user_id":"<demo_prefix>alice","custom":{"seed_key":"<demo_prefix>general:hello-1","seeded_by_skill":true}}}'
```

Generate `seed_key` deterministically per channel + index (`<demo_prefix><channel_short>:hello-1`, `:hello-2`, ...). A second `SendMessage` with the same `seed_key` should be skipped client-side - the Stream API itself does not dedupe on custom fields, so the skip-if-present check above is what makes seeding safe to retry.

Do not send demo messages when the user only asked for credentials or channels.

### Step D - Proceed automatically

After credentials and requested demo data succeed, return to [`SKILL.md`](SKILL.md) and continue into [`builder.md`](builder.md). No additional prompt is needed.

When generating a local demo form, prefill the editable API key, token, user, and channel values from this flow by default. Do not print user tokens in final summaries.

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
- **Never write demo data with generic ids** like `alice`, `bob`, `general`, `random`, `team-alpha`. Generic ids collide with real users/channels in any non-empty Stream app and silently mutate production data. Always apply the per-session `<demo_prefix>` from Step C0.
- **Never skip the Step C0 pre-mutation check.** A misconfigured CLI default can point at a production app - echo the app name + (only) the api key's last 4 chars and require explicit confirmation before seeding into a non-empty app.
- **Never send unmarked demo messages.** Tag with `custom.seeded_by_skill: true` and a deterministic `custom.seed_key`, and run the skip-if-present query before each send so retries do not duplicate the seed.
- **Never send a `user_id` to the customer's token endpoint from the client.** The server must derive the Stream user id from its own authenticated session (see [`sdk.md` > Auth model](sdk.md#auth-model) and the Production auth gate blueprint).
