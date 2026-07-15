# Stream React Native - credentials, token, and demo data

Run this once per session for tracks A, B, and D before writing connected Chat, Video, or Feeds code or creating requested demo data. Track C does not need credentials.

## Goal

Collect the Stream API key, user id, and user token so the app can connect to real Stream data on first run. The API key + token flow is identical for Chat, Video, and Feeds.

- **Chat** can also seed optional **demo data** (channels, users, messages) - see Step C.
- **Video** needs **no demo/seed data**: calls are ephemeral and created at runtime by `client.call(type, id)`, so skip Step C for Video-only sessions and confirm only the API key, user, and token.
- **Feeds** can also seed optional **demo data** (users, follows, activities) - see Step C (Feeds branch). A freshly scaffolded Feeds app renders empty until the connected user has someone to follow and activities to read, so demo data is what makes a new app actually demoable.

For a brand-new app, scaffolding may happen before this file if the runtime or target directory must be resolved first.

This flow uses the **`getstream`** CLI (binary name `getstream`). It is the same `getstream` CLI used across the pack. If the CLI is missing, ask the user to install it from https://getstream.io and wait - never fetch or run an install script yourself.

## Single upfront question (ask exactly once, then act immediately)

Post one message asking all relevant things together. Do not split into multiple rounds. Include question 4 (demo data) **only when Chat is in scope** - for Video-only sessions, drop it (calls need no seed data):

> To wire Stream with real data, I need a few quick answers:
>
> 1. **Credentials** - Should I fetch your API key via the Stream CLI and generate a token, or will you paste them yourself?
> 2. **User** - What user id and display name should the app connect as?
> 3. **Token expiry** - If I am generating the token: should it expire? (for example `1h`, `1d`, `30m`) or never expire?
> 4. **Demo data** *(Chat and Feeds)* - Do you want me to create demo data? For Chat: namespaced channels (and optionally demo users and messages). For Feeds: namespaced demo users, follows from your timeline to their feeds, and a few activities on each so your timeline is not empty. (I will namespace every demo id under a per-session `demo-<random>-` prefix, and confirm with you before writing into a Stream app that already has real data.)
>
> If you want to handle credentials yourself, paste your API key and token (and, for Chat / Feeds, tell me whether to create demo data).

## After the user replies - act without further prompting

Once the user answers, execute the needed CLI steps in sequence without pausing between them. Narrate each step briefly, but do not ask "shall I continue?" between steps. Demo data calls are mutating; run them only when the user asked for them.

### Step A0 - Confirm CLI install and auth

Detect the binary:

```bash
command -v getstream
```

If `getstream` does not resolve, ask the user to install it from https://getstream.io and wait - never fetch or run an install script yourself. Do not continue until `command -v getstream` resolves, unless the user chooses to paste API key and token manually.

Authentication and app selection are handled in Step A below: run the command and follow its output.

### Step A - API key

If the user wants CLI-based credentials:

```bash
getstream env --target expo
```

`getstream env` writes the app's public API key to `.env` as `EXPO_PUBLIC_STREAM_API_KEY`; read it in code with `process.env.EXPO_PUBLIC_STREAM_API_KEY`. You don't need to hold the key yourself, and the secret is never written. (Bare RN CLI without Expo: `getstream env` has no native target yet - inline the public key or wire it through your env library; never the secret.) If `getstream env` reports the project isn't initialized or you're not signed in, run `getstream init`, then re-run it. If the user pastes an API key, use it directly and skip this step.

**Echo the selected app to the user before any mutation:** before running Step C, say `Selected Stream app: "<app_name>" (api_key: <last_4_chars>)` so a misconfigured project is caught before it writes to the wrong app. If the user expected a different app, run `getstream init` to switch it before continuing.

### Step B - Token

Generate a token for the chosen user id. `getstream token` accepts a duration string; omit `--ttl` for a never-expiring local dev token.

```bash
# Never-expiring local dev token
getstream token <user_id>

# Expiring token
getstream token <user_id> --ttl 1h
```

Hold the token in context for code edits. Do not print it in summaries.

If the user pastes a token, hold it in context and skip generation.

### Step C - Demo data (Chat and Feeds, and only if the user asked)

Video needs no demo data - skip this step for Video-only sessions. Chat and Feeds both have a demo-data flow; pick the branch(es) that match the products in scope:

- **Chat** - C1 (users), C2 (channels), C3 (messages)
- **Feeds** - C1 (users, shared with Chat), C4 (follows), C5 (activities), C6 (`foryou` feed group config), C7 (reactions so `foryou` has content)

For Chat, create 3 to 5 channels with realistic usernames; the connected user must be a member of at least one demo channel, or `ChannelList` will render empty. For Feeds, create 3 to 5 demo users, have the connected user's `timeline` follow each of their `user` feeds, post a few activities on each demo user's feed so the timeline has content, configure the `foryou` feed group with the `popular` selector, and seed one reaction per activity so the popular score clears `min_popularity` and `foryou` is not empty on first launch.

These calls are mutating. **All demo ids must be namespaced** so they cannot collide with real users, channels, follows, or activities that already exist in the selected Stream app.

#### C0 - Pre-mutation safety check

Before running any `UpdateUsers` / `GetOrCreateChannel` / `SendMessage` / `GetOrCreateFollows` / `AddActivity` / `UpdateFeedGroup` / `AddActivityReaction`:

1. **Generate a per-session demo prefix** and hold it in context. Default form: `demo-<short_random>-` where `<short_random>` is 4-6 lowercase chars (e.g., `demo-k3p9-`). Every demo user id, channel id, activity id, and seeded record custom field uses this prefix. Do not reuse a prefix across sessions - generate a fresh one each time so retries land in a fresh namespace.
2. **Detect whether the selected app already has real data.** For Chat in scope, run `getstream api QueryChannels --request '{"filter_conditions":{"type":"messaging"},"limit":1}'`. For Feeds in scope, run `getstream api QueryActivities --request '{"limit":1}'`. Check whether either response includes records that do **not** start with a `demo-` prefix.
3. **Confirm explicitly when the app is non-empty.** If real channels or activities exist, surface the count and a sample id, and require the user to type a confirmation before continuing:
   > Selected Stream app `"<app_name>"` already has real data (e.g., `<example_cid_or_activity_id>`). I am about to create demo users / channels / follows / activities namespaced under `<demo_prefix>` so they cannot collide. Confirm with `seed demo` to proceed, or say `cancel`.
4. **Empty / dev app:** announce and proceed without explicit confirmation:
   > Selected Stream app `"<app_name>"` looks empty. Creating namespaced demo data under prefix `<demo_prefix>` now.

If the user cancels, stop Step C and return to Step D with credentials only.

Route demo data through the `getstream` CLI; confirm endpoint and body shapes with `getstream api -h`. Only run mutating calls after the explicit demo-data request and the confirmation above.

#### C1 - Create namespaced user records (shared by Chat and Feeds)

User records must exist before channel membership can be added. Apply the demo prefix to every demo user id (the **token user keeps its own id** - that is the user the app will connect as):

```bash
# <demo_prefix> e.g. demo-k3p9-
getstream api UpdateUsers --request '{"users":{"<token_user_id>":{"id":"<token_user_id>","name":"<display_name>"},"<demo_prefix>alice":{"id":"<demo_prefix>alice","name":"Alice (demo)"},"<demo_prefix>bob":{"id":"<demo_prefix>bob","name":"Bob (demo)"},"<demo_prefix>carol":{"id":"<demo_prefix>carol","name":"Carol (demo)"}}}'
```

`UpdateUsers` is upsert - it is safe to re-run. The same demo users serve both Chat (as channel members) and Feeds (as the owners of `user:<demo_user_id>` feeds that the connected user's timeline will follow).

#### C2 - Create each channel with members (namespaced ids) [Chat]

Use `GetOrCreateChannel`. Prefix every channel id with `<demo_prefix>` and tag the channel with a `seeded_by_skill: true` marker in `data.custom` so later runs can detect this skill's own seeded data:

```bash
getstream api GetOrCreateChannel --type messaging --id <demo_prefix>general --request '{"data":{"created_by_id":"<token_user_id>","members":[{"user_id":"<token_user_id>"},{"user_id":"<demo_prefix>alice"},{"user_id":"<demo_prefix>bob"}],"custom":{"name":"General (demo)","seeded_by_skill":true,"demo_prefix":"<demo_prefix>"}}}'
```

Use namespaced channel ids such as `<demo_prefix>general`, `<demo_prefix>random`, `<demo_prefix>team-alpha`. Make sure the token user appears in `data.members`. `GetOrCreateChannel` is idempotent on the `(type, id)` pair - re-running with the same prefix returns the existing channel rather than duplicating it.

After creating demo channels, summarize without secrets and **without printing user tokens**:

> Created demo channels in `"<app_name>"`: `<demo_prefix>general` (<token_user_id>, <demo_prefix>alice, <demo_prefix>bob), `<demo_prefix>random` (<token_user_id>, <demo_prefix>carol), `<demo_prefix>team-alpha` (<token_user_id>, <demo_prefix>alice)

#### C3 - Send demo messages idempotently (only if the user asked for messages or more demo data) [Chat]

Use `SendMessage` (confirm its body shape with `getstream api SendMessage -h`). Each message's `user_id` must belong to an existing user (so use the namespaced demo users from C1, or the token user). Tag every seeded message with a stable `custom.seed_key` so a re-run can detect and skip already-seeded messages. Don't try to backdate messages.

Before sending, check whether the channel already contains a message with the same `seed_key`:

```bash
# Skip-if-present check (one query per (channel, seed_key)):
getstream api QueryChannels --request '{"filter_conditions":{"type":"messaging","cid":"messaging:<demo_prefix>general"},"messages_limit":50}'
# If the returned messages already include one whose custom.seed_key matches
# <seed_key>, skip the send for that key.
```

Then send only the missing messages:

```bash
getstream api SendMessage --type messaging --id <demo_prefix>general --request '{"message":{"text":"Hello from Alice","user_id":"<demo_prefix>alice","custom":{"seed_key":"<demo_prefix>general:hello-1","seeded_by_skill":true}}}'
```

Generate `seed_key` deterministically per channel + index (`<demo_prefix><channel_short>:hello-1`, `:hello-2`, ...). A second `SendMessage` with the same `seed_key` should be skipped client-side - the Stream API itself does not dedupe on custom fields, so the skip-if-present check above is what makes seeding safe to retry.

Do not send demo messages when the user only asked for credentials or channels.

#### C4 - Have the connected user's timeline follow each demo user [Feeds]

A `timeline` feed only renders activities from feeds it follows, so a Feeds app stays empty until the connected user's timeline follows somebody. Use `GetOrCreateFollows` (idempotent batch upsert) to set up follows from `timeline:<token_user_id>` to each demo user's `user:` feed:

```bash
getstream api GetOrCreateFollows --request '{"follows":[{"source":"timeline:<token_user_id>","target":"user:<demo_prefix>alice"},{"source":"timeline:<token_user_id>","target":"user:<demo_prefix>bob"},{"source":"timeline:<token_user_id>","target":"user:<demo_prefix>carol"}]}'
```

`GetOrCreateFollows` is upsert - re-running is safe, existing follows are returned without error. The endpoint also broadcasts `FollowAddedEvent` only for newly created follows, so re-runs do not double-fire notifications.

If the user wants their own posts on their own timeline (the "self-follow"), the skill's blueprint `OwnFeedsContextProvider` already establishes that client-side on app boot. You can also seed it here by adding `{"source":"timeline:<token_user_id>","target":"user:<token_user_id>"}` to the follows array.

#### C5 - Post demo activities idempotently [Feeds]

For each demo user, post 1-3 activities on their `user:` feed via `AddActivity`. Required fields: `feeds` (target feed array), `type`. Use a deterministic `id` per (user, index) so retries are idempotent - re-running with the same `id` returns the existing activity instead of creating a duplicate.

```bash
getstream api AddActivity --request '{"id":"<demo_prefix>alice-1","feeds":["user:<demo_prefix>alice"],"user_id":"<demo_prefix>alice","type":"post","text":"Just shipped a new feature! Activity feeds are wild.","custom":{"seeded_by_skill":true,"demo_prefix":"<demo_prefix>"}}'
getstream api AddActivity --request '{"id":"<demo_prefix>alice-2","feeds":["user:<demo_prefix>alice"],"user_id":"<demo_prefix>alice","type":"post","text":"Loving the React Native ecosystem lately.","custom":{"seeded_by_skill":true,"demo_prefix":"<demo_prefix>"}}'
getstream api AddActivity --request '{"id":"<demo_prefix>bob-1","feeds":["user:<demo_prefix>bob"],"user_id":"<demo_prefix>bob","type":"post","text":"Stream Feeds makes social apps surprisingly simple.","custom":{"seeded_by_skill":true,"demo_prefix":"<demo_prefix>"}}'
getstream api AddActivity --request '{"id":"<demo_prefix>carol-1","feeds":["user:<demo_prefix>carol"],"user_id":"<demo_prefix>carol","type":"post","text":"Anyone else excited about the new SDK?","custom":{"seeded_by_skill":true,"demo_prefix":"<demo_prefix>"}}'
```

Generate ids deterministically per user + index (`<demo_prefix>alice-1`, `:alice-2`, ...). Tag every seeded activity with `custom.seeded_by_skill: true` and `custom.demo_prefix: <demo_prefix>` so later runs can identify this skill's seeded data.

After the follows and activities are in place, the connected user's timeline will render the demo users' posts on first launch.

#### C6 - Configure the `foryou` feed group [Feeds]

`foryou` ships with no `activity_selectors` configured, so the connected user's `foryou` feed returns empty until a selector is set on the group. `UpdateFeedGroup` is idempotent (PUT) - safe to re-run with the same body.

```bash
# `popular` formula: reactions + comments*2 + bookmarks*3 + shares*3.
# min_popularity: 1 means "at least one reaction-equivalent in cutoff_window".
# cutoff_window 7d is the default but worth making explicit so the selector
# does not silently drift if defaults change.
getstream api UpdateFeedGroup --id foryou \
  --request '{"activity_selectors":[{"type":"popular","min_popularity":1,"cutoff_window":"7d"}]}'
```

This is a **server-side config on the feed group itself**, not on a per-user feed. It applies to every `foryou:<user_id>` feed in the app. Once configured, every user's `foryou` feed will return activities that match the selector.

#### C7 - Seed one reaction per activity [Feeds]

The `popular` selector picks activities by their popularity score. A freshly seeded activity has score 0, so it does not clear `min_popularity: 1` and does **not** appear in `foryou` even after C6. Adding one reaction per activity bumps the score to 1 and makes the activity eligible. Use `AddActivityReaction` (one call per activity). Use a non-`<token_user_id>` reactor (e.g. carol reacts to alice) so the demo looks realistic - the connected user does not see their own reaction pre-filled on every post.

```bash
getstream api AddActivityReaction --activity-id <demo_prefix>alice-1 --request '{"type":"like","user_id":"<demo_prefix>carol"}'
getstream api AddActivityReaction --activity-id <demo_prefix>alice-2 --request '{"type":"like","user_id":"<demo_prefix>bob"}'
getstream api AddActivityReaction --activity-id <demo_prefix>bob-1 --request '{"type":"like","user_id":"<demo_prefix>alice"}'
getstream api AddActivityReaction --activity-id <demo_prefix>carol-1 --request '{"type":"like","user_id":"<demo_prefix>alice"}'
```

`AddActivityReaction` is **not** idempotent by default - a second call with the same `(activity_id, type, user_id)` will fail with "reaction already exists" or, with `enforce_unique: true`, replace the existing reaction. The safest pattern for re-runs is to skip silently on the "already exists" error rather than crash the seeding flow. Adding more variety (`type: "love"` from one user, `type: "like"` from another) is fine - the popularity formula counts all reactions equally.

After C6 + C7, summarize without printing tokens:

> Configured `foryou` feed group with `popular` selector (`min_popularity: 1`, `cutoff_window: 7d`). Seeded 1 like per demo activity so they clear the popularity threshold. The connected user's `foryou` tab should render these on first launch.

Do not run C4 through C7 when Feeds is not in scope, or when the user only asked for credentials. If only C4 + C5 ran (timeline-only demo, no Explore tab), `foryou` stays empty and that is fine - the Home tab still works.

### Channel-type configuration - disable threads (optional) [Chat]

<a id="disable-threads"></a>Some feature toggles live on the **channel type**, not on the client. Thread replies are one: whether the SDK surfaces a reply-in-thread affordance is governed by the `replies` setting on the `messaging` channel type (enabled by default). If a design has no threads (see the thread scope gate in [`references/design-matching.md`](references/design-matching.md)), turn them off at the source so the UI never offers a thread action the design lacks:

```bash
# Confirm the body shape first, then disable thread replies on the messaging type.
getstream api UpdateChannelType -h
getstream api UpdateChannelType --name messaging --request '{"replies":false}'
```

- This is a **mutating, app-wide** setting - it affects **every** channel of the `messaging` type, not just demo channels. Only run it on a fresh / scaffold app, or after the same non-empty-app confirmation gate as Step C0. Do not silently reconfigure a channel type in an app that already has real data.
- Follow the CLI-safety rule (confirm the endpoint and body with `getstream api UpdateChannelType -h` before running; only mutate after the user confirms no threads).
- Reversible and symmetric: re-enable with `--request '{"replies":true}'`.

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
