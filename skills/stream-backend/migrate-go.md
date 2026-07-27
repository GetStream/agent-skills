# Migrate Go: stream-chat-go to getstream-go

Migrate a Go server integration from `github.com/GetStream/stream-chat-go` (legacy, maintenance mode) to `github.com/GetStream/getstream-go` (generated from the OpenAPI spec, actively developed).

**Docs-driven and read-only until you have fetched the guide.** Never migrate from memory. The official guide below is the source of truth for every mapping; this file is only the procedure that drives it.

> The legacy SDK is not going away, so a partial migration is safe: code you have not converted keeps compiling against the old import. Convert in whole operations, verify, then move on.

---

## G1: Detect what is installed

Read the real state, do not guess:

```bash
cat go.mod
grep -rn "GetStream/stream-chat-go" --include=*.go .
```

Establish:
- The legacy module + major version in `go.mod` (e.g. `github.com/GetStream/stream-chat-go/v8`).
- The **import alias** used in the code (commonly `stream`), so you rename every reference, not just the import line.
- The **call sites**: every method invoked on the legacy client or channel object. This list is the migration's work-list and its done-check.

Target module: `github.com/GetStream/getstream-go/v4` (confirm the latest major before editing).

## G2: Fetch the guide (before any edit)

`WebFetch` the guide, starting with the README (it carries the key differences and the topic index), then the topic files that match the detected call sites:

- Index + key differences: `https://raw.githubusercontent.com/GetStream/getstream-go/main/docs/migration-from-stream-chat-go/README.md`
- `01-setup-and-auth.md` - client init, env vars, tokens, sub-clients
- `02-users.md` - upsert, query, partial update, deactivate, delete
- `03-channels.md` - create, distinct, query, members, update, delete, query members
- `04-messages-and-reactions.md` - send, reply, get, update, delete, react
- `05-moderation.md` - moderators, ban, mute, shadow ban, query banned
- `06-devices.md` - add, list, delete push devices

Same base URL, swap the filename. **Hard gate:** if the guide does not load, stop and tell the user you could not fetch the migration guide; do not proceed from memory.

## G3: Plan against the guide

Map each call site from G1 to a section of the guide. Two outcomes only:

1. **Covered** by the guide -> queue the documented transform.
2. **Not covered** (e.g. Video, Feeds, file/attachment uploads, search, events/webhooks, permissions/roles, blocklists, commands, import/export, and anything else absent from the six topics) -> **do not invent a mapping**. Collect these and either stop for guidance or leave them untouched and list them as manual follow-ups. Flag this explicitly in the report.

## G4: Apply the transforms

Work from the fetched guide, operation by operation. These recurring rules from the README's Key Differences apply throughout, but the per-operation detail always comes from the topic file:

- **Module + alias:** `stream-chat-go/v8` -> `getstream-go/v4`; alias `stream` -> `getstream` on every reference.
- **Env vars:** `STREAM_KEY` -> `STREAM_API_KEY`, `STREAM_SECRET` -> `STREAM_API_SECRET`.
- **Sub-clients:** root-client methods move under `client.Chat()`, `client.Moderation()`, `client.Video()`, `client.Feeds()`. The channel object is `client.Chat().Channel(type, id)`.
- **Request structs:** flat structs become typed `*Request` types; content is nested (e.g. `SendMessageRequest{ Message: MessageRequest{...} }`).
- **Pointers:** optional scalar fields are pointers - wrap with `getstream.PtrTo(value)`.
- **Custom data:** `ExtraData` -> `Custom` maps.
- **Functional options** (`stream.BanWithReason(...)`, `stream.WithHardDelete()`) become **fields on the request struct**.
- **Responses:** reshape to `resp.Data.*` (e.g. `resp.User` -> `resp.Data.Users[id]`, `resp.Message` -> `resp.Data.Message`).

**Behavioral changes to call out, not just rewrite** (these change runtime semantics, so the user must be told):
- Some single, synchronous calls become **batch + async** and return a `TaskID` to poll: `DeleteUser` -> `DeleteUsers`, `DeleteChannels`. Code that assumed the delete was complete on return must now track the task.
- Members go from `[]string` to `[]ChannelMemberRequest{{UserID: ...}}`.
- A distinct (empty-ID) channel create becomes the dedicated `GetOrCreateDistinctChannel`.
- `AddMembers` / `RemoveMembers` / `AddModerators` / `DemoteModerators` are no longer methods; they are fields on `ch.Update(&UpdateChannelRequest{...})`.
- `PushProvider` typed constants become plain strings (`"firebase"`, `"apn"`).

After each operation, `grep` the codebase for the legacy symbol to confirm nothing was missed:

```bash
grep -rn "<oldSymbol>" --include=*.go .
```

Do not add features or refactor beyond the migration - this is a like-for-like port.

## G5: Verify (the backstop)

```bash
go mod tidy
go build ./...
go vet ./...
gofmt -l .
```

Fix every error the migration surfaced and re-run until `build` and `vet` are clean. This step is what catches an incorrect mapping the guide did not prevent - do not declare the migration done until it passes.

## G6: Report

State plainly:
- Module bumped: `stream-chat-go/v8` -> `getstream-go/v4`, and env var renames if the app reads them.
- Operations migrated, grouped by topic.
- **Behavioral changes** the user must handle (async delete + `TaskID` polling, any semantics that shifted).
- **Uncovered call sites** left untouched (Video/Feeds/uploads/search/etc.) with a note that the guide does not cover them yet.
- Verification result (`go build` / `go vet` output).

Offer, do not auto-run, the natural next step (e.g. "want me to look at the Video calls the guide did not cover, against the live docs?").
