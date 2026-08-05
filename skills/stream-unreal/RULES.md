# Stream Unreal - non-negotiable rules + Unreal pitfalls

Every rule below is stated once. Read it before writing code. The docs cover *how* to call each API; this file covers what the docs do not say and what fails silently.

---

## Scope and honesty

- **Chat only.** No Stream Video or Feeds SDK exists for Unreal. Do not route to `/video/docs/...` or `/activity-feeds/docs/...` and do not invent an Unreal calling API.
- **Beta.** The plugin declares `IsBetaVersion: true`. Say so when the user pins a version, plans an upgrade, or asks how stable the surface is.
- **Say no before writing code.** Run the feature gate in [`SKILL.md`](SKILL.md) Gate 2 first. Emitting `Channel->SendAttachment(...)` and letting the compiler explain that attachments do not exist is the failure mode this rule prevents.
- **Never translate a JavaScript doc snippet into C++.** Most `/chat/docs/unreal/` pages carry JS-only code (see [`SKILL.md`](SKILL.md) "the coverage caveat"). A JS snippet tells you the concept, never the signature. Read the header instead.
- **Engine support is 5.7 and 5.8 only.** 4.27/5.0/5.1 need v1.3.0; **5.2 through 5.6 have no release at all** - that is a hard stop, stated immediately, not worked around.

## Secrets and auth

- The client holds only the **API key** and a **user token**. The API **secret** never goes into game code, `Config/*.ini`, a `.uasset`, or chat - it stays server-side / in the CLI.
- Token model: backend-issued token via an `ITokenProvider` in production; a CLI token (`getstream token <user_id>`, optionally `--ttl <duration>`) for local/demo; a static pasted token only when the user insists.
- **A hardcoded token must carry a comment saying why it is wrong for production**: it ships to every device, cannot be rotated or revoked, and defeats token refresh (the SDK has nothing to call when it expires).
- `UStreamChatClientComponent::DevToken(UserId)` is **development only** - it requires the app to have auth checks disabled, which means any client can impersonate any user. Never ship it.
- Never invent or fabricate credentials. In generated code, reference them through named constants or `Config` `UPROPERTY`s, never inline literals scattered across files.
- User ids may contain only `a-z`, `0-9`, `@`, `_`, and `-`.

## THE headline rule: `ApiKey` must be set before `BeginPlay` runs

`UStreamChatClientComponent` builds its REST client in `BeginPlay` but its websocket in `ConnectUser`:

```cpp
// UStreamChatClientComponent::BeginPlay()
Api = FChatApi::Create(ApiKey, GetDefault<UStreamChatSettings>()->Host, TokenManager);
//                     ^^^^^^ captured HERE

// UStreamChatClientComponent::ConnectUserInternal()
Socket = IChatSocket::Create(TokenManager.ToSharedRef(), ApiKey, ...);
//                                                       ^^^^^^ captured LATER
```

Set `ApiKey` *after* `Super::BeginPlay()` and you get a client that **looks like it works**: `ConnectUser` succeeds, the websocket connects, the callback fires with a valid `FOwnUser` - and then every REST call 401s:

```
LogHttpClient: Error: HTTP request returned an error
  [StatusCode=401, Verb=POST, Url=https://chat.stream-io-api.com/channels/messaging/x/query?api_key=]
LogTemp: Error: API error response
  [Code=2, Message=GetOrCreateChannel failed with error: "api_key or app_id not provided"]
```

The empty `api_key=` in the URL is the tell. Because connect succeeded, this reads as a permissions or channel-type problem. It is neither.

**Rule: never emit `Client->ApiKey = ...` after a `Super::BeginPlay()` call.** The three correct placements:

```cpp
// 1. In the owning actor's constructor - what the docs and the sample do.
AMyHud::AMyHud()
{
    Client = CreateDefaultSubobject<UStreamChatClientComponent>(TEXT("Client"));
    Client->ApiKey = TEXT("your_api_key");   // a literal is fine here
}

// 2. Above Super::BeginPlay() - REQUIRED if the key comes from a Config UPROPERTY,
//    because Config properties are copied from the CDO AFTER the C++ constructor body runs,
//    so ApiKey is still empty in the constructor.
void AMyHud::BeginPlay()
{
    Client->ApiKey = ApiKey;   // must precede Super, which dispatches component BeginPlay
    Super::BeginPlay();
}

// 3. Not in code at all. ApiKey is a Config UPROPERTY on the component, so DefaultEngine.ini
//    works and the CDO loads it before BeginPlay:
//    [/Script/StreamChat.StreamChatClientComponent]
//    ApiKey=your_api_key
```

If the key is config-driven, emit it above the `Super::` line **with a comment saying why**. This is the highest-value single rule in this skill: the symptom does not point at the cause.

## Client lifetime: on the HUD, torn down in EndPlay

`UStreamChatClientComponent` is an `ActorComponent` whose own class comment says "Should be added to a client-side actor, e.g. HUD." The HUD is right because it is created per local player, exists only on the client, and is torn down with the player - which is exactly a chat connection's lifetime.

- **Never put it on a replicated actor.** That opens one websocket per connected player.
- **Always `DisconnectUser()` in `EndPlay`.** Without it the socket is only torn down at GC, which in PIE means the previous session's connection outlives the session and the user stays online.
- **One client per game instance.** Do not create a second component, and do not create one in a widget, a Blueprint function that re-runs, or a per-frame path.

```cpp
void AMyHud::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Client) { Client->DisconnectUser(); }
    Super::EndPlay(Reason);
}
```

## Async callbacks: always `TWeakObjectPtr`, never raw `this`

Every C++ API is callback-based (`TFunction<void(...)>`) and fires on the game thread once the HTTP/WS response lands. The owning actor can die first - level change, PIE stop, travel.

```cpp
Client->ConnectUser(User, Token,
    [WeakThis = TWeakObjectPtr<AMyHud>(this)](const FOwnUser& OwnUser)
    {
        if (!WeakThis.IsValid()) { return; }
        // safe to touch UObjects here - this is the game thread
    });
```

**Never emit a raw `this` capture in a Stream callback**, and **always check `IsValid()` before the first dereference** - including in nested callbacks, where the outer check does not cover the inner one. (The shipped `StreamChatSampleHud.cpp` captures a `TWeakObjectPtr` but then dereferences it without checking; do not copy that part.)

Because callbacks land on the game thread, no `AsyncTask(ENamedThreads::GameThread, ...)` hop is needed - do not add one.

## Module dependencies: depend on almost nothing

The plugin ships 10 modules; a game module needs at most two:

```csharp
// <Project>.Build.cs
PrivateDependencyModuleNames.AddRange(new[] {
    "StreamChat",     // the ONLY module needed for the client + channel + user API. Transitively
                      // pulls StreamChatApi, StreamChatWebSocket, StreamChatDto, TokenProvider,
                      // HttpRequests, StreamJson.
    "StreamChatUi",   // ONLY if you reference the UMG widget C++ classes
    "UMG",            // needed alongside StreamChatUi (CreateWidget, UUserWidget)
});
```

`StreamChat` alone compiles `UStreamChatClientComponent`, `UChatChannel`, `FUser`, `FFilter`. Do not add `StreamChatApi`, `StreamChatDto`, or `StreamChatWebSocket` directly - depending on the internals is how a project breaks on the next beta release. Never depend on `StreamChatApiTest` or `StreamChatEditor` from a game module.

## No wrapper or bridge abstractions

Do not introduce `StreamChatManager`, `ChatSubsystem` wrappers, `StreamWrapper`, or an `IChatService` interface over the SDK. Use the SDK types directly: `UStreamChatClientComponent` on the HUD, `UChatChannel*` handles, `FFilter` for queries, the shipped widgets for UI. A `UGameInstanceSubsystem` is only justified if the user explicitly asks for chat to survive level transitions - and even then it holds the component, it does not re-export its API.

## Project ownership

Preserve the project's existing shape. Do not convert a Blueprint project to C++ or vice versa, do not restructure `Source/`, do not change the default `GameMode`/`HUD`/map unless that *is* the request, and do not reformat unrelated files (the repo lints with a pinned `clang-format`). If there is no Unreal project at all, tell the user to create it in the Unreal Editor first - do not hand-write a `.uproject`.

## Mindful API usage

The SDK talks to a rate-limited, billed backend.

- **Query once, then watch.** One `QueryChannels` with a filter + sort + sensible page size, then rely on `EChannelFlags::Watch` and WebSocket events for live updates. Do not re-query on every event, every `Tick`, or every widget construction.
- **`EChannelFlags::Watch` is not optional in practice.** Without it no websocket events arrive for those channels and **new messages never appear**. `State | Watch` is the default for a reason - keep it unless the user has a read-only one-shot need.
- **Never call a Stream API from `Tick`,** from a Blueprint `Event Tick`, or from a widget's `NativePreConstruct`/`Construct` (which re-run).
- **Connect once.** One `ConnectUser` per session; for expiring tokens supply an `ITokenProvider` and let the SDK refresh. Never poll, never reconnect on a timer, never connect/disconnect in a loop.
- **Paginate** with `QueryAdditionalChannels` / `QueryAdditionalMessages` instead of asking for huge pages. `QueryChannels` limit is capped at 30 channels; message limit at 300; member limit at 100.
- **Back off on errors** instead of retrying tightly. There is a per-app query-channels budget on top of global rate limits.

For a high-volume in-game or livestream surface, read the livestream best-practices page ([`docs-map.md`](docs-map.md)) before scaling: use the `livestream` channel type, turn off read events / typing indicators / connect events, and enable slow mode.

## Permissions: match the channel type to the vertical

Stream ships channel types with sensible default policies. Start from the one that fits instead of hand-rolling permissions:

| Vertical | Channel type | Default posture |
|---|---|---|
| Party / squad / DM chat | `messaging` | Membership-gated: members read and write |
| Guild / clan / team spaces | `team` | Membership + roles for broader spaces |
| Global in-game chat, spectator chat | `gaming` | Game-tuned defaults |
| Livestream / watch-party chat | `livestream` | Public read/write without membership; supports guest + anonymous viewers |
| Commerce / live shopping | `commerce` | Commerce defaults |

- **Read-only spectators** connect as **anonymous** (`ConnectAnonymousUser` - read-only, can read `livestream` channels, no MAU cost) or **guest** (`ConnectGuestUser` - limited writes, pre-account, does count toward MAU). Do not mint a full per-user JWT for every spectator.
- Moderate with the `channel_moderator` role, never by giving a client the `admin` role.
- **Permission checks apply to client-side calls only** - server-side calls with the API secret bypass them all. Never rely on client permissions to protect anything, never give the game the secret.
- Customize policies in the Dashboard or via the server API, never from game code.

## C++ / Blueprint asymmetry

Many operations exist twice with different shapes. Do not assume a C++ signature is callable from Blueprint or vice versa - check the `UFUNCTION` macro in the header.

- **C++**: `TFunction` callbacks, `TOptional<>` parameters, full pagination.
- **Blueprint**: latent nodes (`meta = (Latent, WorldContext, LatentInfo)`) with `Out` params, and `...BP`-suffixed variants where the C++ signature uses `TOptional` - `SendMessageBP`, `GetMessageBP`, `BanUserBP`, `ShadowBanUserBP`, `MuteUserBP`, `BanMemberBP`.
- **C++ only**: pagination (`QueryAdditionalChannels`, `QueryAdditionalMessages`, `GetReactions`, `QueryBannedUsers`), `QueryUsers`, `SearchMessages` on the client, `ListDevices`, `GetBlockedUsers`, `ConnectUser` with an `ITokenProvider`, and the templated event subscription (`Client->On<FMessageNewEvent>(...)`).
- Naming trap: zero `FTimespan` in a `...BP` ban/mute means **unlimited**, not "immediately expired".

Tell a Blueprint-only user which parts of their request will need C++ **before** starting.

## Docs discipline

The live Unreal docs are the source of truth *where they have Unreal code*; the plugin headers are the source of truth everywhere else. Do not answer SDK specifics from training data. Cite the page or the header path. Never guess a class, method, enum, or asset-path name - `FChannelProperties`, `EChannelFlags`, `EChannelSortField`, `FFilter::In` all look guessable and the near-misses are routinely wrong.

---

## Unreal pitfalls (the ones that fail silently)

Full procedures live in the runbooks; these are the traps, stated once.

### The UI widgets are Blueprint assets, not C++ classes

The C++ widget classes (`UTeamChatMobileWidget`, `UInGameChatWidget`, `UChannelListWidget`, ...) are effectively abstract: their `UPROPERTY(meta = (BindWidget))` members are only satisfied by the widget tree inside the plugin's Blueprint assets. **Instantiating the C++ class directly yields a widget with every bound pointer null, which renders as nothing, with no error.** Load the Blueprint class by path (note the `_C` suffix) instead. See [`widgets.md`](widgets.md).

### `Setup()` must precede `AddToViewport()`

`AddToViewport()` triggers `NativePreConstruct`, which is where the channel list's Slate list view is built - but only `if (GetClient() && ListView)`, and `GetClient()` walks up to a `UClientContextWidget` that only `Setup` populates. Call `Setup` afterwards and the list is never built, **nothing rebuilds it later**, and the widget renders empty forever with no log line. Order is `CreateWidget` -> `Setup(...)` -> `AddToViewport()`. See [`widgets.md`](widgets.md).

### The channel list does not load itself

`UChannelListWidget` binds to `GetClient()->GetChannels()` and **never queries**. Show it without calling `QueryChannels` first and it is permanently empty, with no error. Correct order: `ConnectUser` -> (optional `WatchChannel` to seed) -> `QueryChannels` -> create + `Setup` the widget.

### Path-loaded content needs an explicit cook directive

Loading widgets by path means nothing in the project references them, so the cooker drops them and the packaged build finds no widget class - it works in the editor and breaks when packaged, the worst class of bug to ship. Any `LoadClass` on a `/StreamChat/...` path **must** be paired with `DirectoriesToAlwaysCook` entries in `DefaultGame.ini`. See [`widgets.md`](widgets.md) and [`platforms.md`](platforms.md).

### `Setup` signatures differ per widget, and widgets get their client from an ancestor

`UTeamChatMobileWidget::Setup(UStreamChatClientComponent*)` and `UTeamChatWidget::Setup(UStreamChatClientComponent*)` are self-contained (they own a `ClientContextWidget`). `UChannelWidget::Setup(UChatChannel*)` and `UInGameChatWidget::Setup(UChatChannel*)` take a **channel** and must sit under a `UClientContextWidget`. Anything you compose by hand outside that hierarchy sees a null client. Also: `UStreamWidget::Initialize()` calls `OnSetup()` itself when `Setup` was never called, so `OnSetup` can run twice - keep overrides idempotent.

### A packaged build cannot reach Stream without `n.VerifyPeer=True`

`[/Script/Engine.NetworkSettings] n.VerifyPeer=True` in `DefaultEngine.ini` is what makes UAT stage the
engine's CA certificates into a packaged build. Absent, every `wss://` connection fails with
`SSL error: unable to get local issuer certificate` and the client retries forever. The editor reads the
engine's copy from disk, so this is invisible until you package. Applies to **every** platform. See
[`platforms.md`](platforms.md) 1b.

### Mobile packaging config is load-bearing, and one file fails silently

Four settings across two files decide whether a packaged iOS build is usable at all - without them it is unreadably small, freezes a few frames in, or never sees a touch. `UInputSettings` is `config=Input`, so the touch/mouse-capture keys **only** work in `Config/IOS/IOSInput.ini`; putting them in `IOSEngine.ini` is a silent no-op. See [`platforms.md`](platforms.md).

### iOS signing: the documented setting is the wrong one on UE 5.5+

`bAutomaticSigning` / `IOSTeamID` under `[/Script/IOSRuntimeSettings.IOSRuntimeSettings]` feed the *legacy* Xcode generator and are **silently ignored** by the modern one (default since ~5.5). The section that works is `[/Script/MacTargetPlatform.XcodeProjectSettings]`. And **stop and ask for the team ID** rather than guessing - automatic signing registers an App ID on the user's Apple Developer account, which is not a reversible local change. See [`platforms.md`](platforms.md).

### `Build.sh <Target> IOS` does not produce a runnable app

It compiles and links only - never cooks or stages - so the `.app` it produces has no cooked assets and no `.uproject`, and crashes on launch with `Failed to open descriptor file`. It is a compile check, nothing more. Anything the user will actually run goes through `RunUAT.sh BuildCookRun`. Never describe a `Build.sh` artifact as deployable. See [`platforms.md`](platforms.md).

### Two environment traps when verifying your own work

- **Cloning the SDK repo needs Git LFS.** All `.uasset`/`.umap` are LFS-tracked; without it you get 129-byte pointer files and `The summary for the package ... is invalid`. The release **zips** are unaffected - only clones.
- **On macOS `UnrealEditor` re-execs and detaches**, so the launching shell exits ~1 and a stdout redirect captures only the stub. Pass `-unattended -log -stdout` to keep it in the foreground, or a wrapper script will report a failure that did not happen.
- Each engine version accepts only a range of Xcode versions (Epic's constraint, not the SDK's). `Platform Mac is not a valid platform to build` means Xcode is outside that range; the range lives in `Engine/Config/Apple/Apple_SDK.json`.

### Two log lines that verify a healthy first run

- **`api_key=` in the websocket URL must be non-empty.** Fastest confirmation the key landed (see the `ApiKey`/`BeginPlay` rule).
- **Zero `LogUMG` warnings means every `BindWidget` was satisfied.** A failed binding always logs there, so a clean `LogUMG` is real evidence the widget tree built correctly.
