# Stream Unreal - setup flow (integrate / new project)

Run this once per session for integrate or new-project requests, before feature work. How-to / reference requests skip it entirely. Obey [`RULES.md`](RULES.md) throughout, and make sure [`SKILL.md`](SKILL.md) Step 0's three gates passed first - **the engine version decides which archive you download**, so it is not optional here.

---

## 1. Project signals (read-only probe)

```bash
bash -c 'echo "=== UPROJECT ==="; find . -maxdepth 3 -name "*.uproject" -print 2>/dev/null; \
echo "=== ENGINE ==="; find . -maxdepth 3 -name "*.uproject" -exec grep -m1 -H EngineAssociation {} \; 2>/dev/null; \
echo "=== C++ MODULES ==="; find . -maxdepth 4 -name "*.Build.cs" -print 2>/dev/null; \
echo "=== EXISTING PLUGIN ==="; find . -maxdepth 3 -name "StreamChat.uplugin" -print 2>/dev/null; \
echo "=== CONFIG ==="; ls Config 2>/dev/null'
```

Interpret and hold in context:

- **`.uproject` + `Source/*.Build.cs`** -> C++ project. The full surface is available.
- **`.uproject`, no `Source/`** -> Blueprint-only project. Say which parts of the request will need C++ (pagination, lower-level APIs, event templates - [`RULES.md`](RULES.md) "C++ / Blueprint asymmetry") and offer to add a C++ module. Note that adding one requires the user to have a compiler toolchain installed (Xcode on macOS, Visual Studio on Windows).
- **`Plugins/StreamChat/StreamChat.uplugin` already present** -> this is an upgrade or a feature addition, not a fresh install. Read its `VersionName` and `EngineVersion` before changing anything, and check both against the target engine.
- **No `.uproject`** -> **stop.** Tell the user to create the project in the Unreal Editor (or Epic launcher) first, picking a 5.7 or 5.8 engine. Do not hand-write a `.uproject`.

State a one-line status, e.g. `UE 5.7 C++ project detected - StreamChatDemo.uproject - ready for the plugin`.

---

## 2. Install the plugin

Distribution is **GitHub Releases, source only** - no prebuilt binaries, and it is not on Fab/Marketplace for new installs. There is **one archive per engine version**, and picking the wrong one is a silent mismatch:

| Asset | Engine |
|---|---|
| `StreamChat-5.7.zip` | 5.7 (its `.uplugin` declares `"EngineVersion": "5.7.0"`) |
| `StreamChat-5.8.zip` | 5.8 |

```bash
# Confirm what the latest release actually ships before downloading
gh release view --repo GetStream/stream-chat-unreal --json tagName,assets \
  --jq '{tag: .tagName, assets: [.assets[].name]}'

# Then take the archive matching the engine resolved in Gate 1
gh release download v2.0.0 --repo GetStream/stream-chat-unreal --pattern "StreamChat-5.7.zip" --dir /tmp
unzip -q /tmp/StreamChat-5.7.zip -d /tmp/streamchat
mkdir -p Plugins && cp -R /tmp/streamchat/StreamChat Plugins/
```

Without `gh`, point the user at https://github.com/GetStream/stream-chat-unreal/releases/latest and have them drop the `StreamChat` folder into `<Project>/Plugins/`.

The folder name must stay **`StreamChat`** - the plugin's content root is `/StreamChat/`, and every asset path in [`widgets.md`](widgets.md) depends on it.

Then:

1. Confirm the plugin is enabled - it is enabled by default once present, but verify in **Edit > Plugins > Stream Chat** (or check for a `Plugins` entry in the `.uproject` disabling it).
2. Regenerate project files and compile the editor target (see 6).

**Two notes worth stating rather than discovering:**

- The release archives set `"Installed": true` in `StreamChat.uplugin`. That normally marks an engine/Marketplace plugin. It does **not** break a project build, but it makes the editor treat the plugin as read-only - surprising for a source drop into `Plugins/`. Do not "fix" it unless the user wants to edit plugin source, in which case flipping it to `false` is the change.
- `.uproject`/`.uplugin` files differ per engine version in the repo (`just set-engine 5.8` swaps them). Only relevant if the user clones the SDK repo rather than using a release zip - and a clone needs **Git LFS** ([`RULES.md`](RULES.md)).

### 2b. Module dependencies

Add to the game module's `.Build.cs` - and nothing more (see [`RULES.md`](RULES.md) "Module dependencies"):

```csharp
PrivateDependencyModuleNames.AddRange(new[] {
    "StreamChat",     // client + channel + user API; pulls the rest transitively
    "StreamChatUi",   // only if you reference the widget C++ classes
    "UMG",            // needed alongside StreamChatUi
});
```

For a Blueprint-only integration, skip this step entirely - the plugin's own modules are already loaded.

---

## 3. Credentials (ask once, then act)

Collect the API key, a user token, and optional seed channels in **one** message, then execute without pausing between steps:

> To wire this with real data I need: (1) should I fetch your API key and mint a token via the Stream CLI, or will you paste them? (2) token expiry (`1h`, `1d`, never)? (3) seed a couple of channels so chat shows data on first launch?

If the user says they will paste credentials, take them and skip the CLI.

```bash
# Onboard ONCE in the project dir: authenticate + select/create org & app + write credentials.
# REQUIRED first - token/api all fail with "stream project is not initialized" otherwise.
getstream init

# Mint a user token (never-expiring, or add --ttl <duration>)
getstream token sam
getstream token sam --ttl 2h

# Seed users, then channels. Pick --type to match the vertical (see RULES.md "Permissions"):
# messaging for party/DM, team for guild, gaming for global in-game, livestream for spectator chat.
getstream api UpdateUsers --request '{"users":{"sam":{"id":"sam","name":"Sam"},"alice":{"id":"alice","name":"Alice"}}}'
getstream api GetOrCreateChannel --type messaging --id general \
  --request '{"data":{"created_by_id":"sam","members":[{"user_id":"sam"},{"user_id":"alice"}]}}'
getstream api SendMessage --type messaging --id general \
  --request '{"message":{"user_id":"alice","text":"Hey, welcome in."}}'
```

`getstream env` writes platform env files and has no Unreal target, so **do not use it here** - carry the API key into Unreal config instead (below). Make the token user a member of at least one channel so chat shows data on first launch. Print a one-line summary of what was created. Never put the API **secret** in game code. If a CLI step fails, explain briefly and ask the user to paste the missing value.

### Where the credentials live in an Unreal project

There is no `.env`. Two reasonable homes, both of which respect the `ApiKey`-before-`BeginPlay` rule:

**Config (preferred - no rebuild to change it, and the CDO loads it before `BeginPlay`):**

```ini
; Config/DefaultEngine.ini - ApiKey is a Config UPROPERTY on the component
[/Script/StreamChat.StreamChatClientComponent]
ApiKey=your_api_key
```

**A `Config` UPROPERTY on your own actor,** when you also want the user id and token configurable:

```cpp
// MyHud.h
UPROPERTY(EditDefaultsOnly, Config, Category = "Stream Chat")
FString ApiKey;
UPROPERTY(EditDefaultsOnly, Config, Category = "Stream Chat")
FString UserId;
UPROPERTY(EditDefaultsOnly, Config, Category = "Stream Chat")
FString UserToken;   // demo only - see RULES.md "Secrets and auth"
```

Either way: **a checked-in token is a demo shortcut, not a shipping pattern.** Emit the comment saying so, and offer the `ITokenProvider` path (4b) for anything real.

---

## 4. Wire the client

This is the verified minimal integration: connect, seed a channel, query, show UI. It compiles and runs against a live Stream backend, and it is the pattern the SDK's own sample uses.

```cpp
// MyHud.h
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/HUD.h"
#include "StreamChatClientComponent.h"

#include "MyHud.generated.h"

UCLASS()
class MYGAME_API AMyHud final : public AHUD
{
    GENERATED_BODY()

public:
    AMyHud();

private:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    void ShowChatUi();

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess))
    UStreamChatClientComponent* Client;

    // Config-driven so the values are not compiled in. See setup.md 3.
    UPROPERTY(EditDefaultsOnly, Config, Category = "Stream Chat")
    FString ApiKey;
    UPROPERTY(EditDefaultsOnly, Config, Category = "Stream Chat")
    FString UserId;
    UPROPERTY(EditDefaultsOnly, Config, Category = "Stream Chat")
    FString UserToken;
};
```

```cpp
// MyHud.cpp
#include "MyHud.h"

#include "Channel/ChatChannel.h"
#include "User/OwnUser.h"
#include "User/User.h"

AMyHud::AMyHud()
{
    Client = CreateDefaultSubobject<UStreamChatClientComponent>(TEXT("Client"));
    // ApiKey is NOT set here: Config properties are copied from the CDO after the constructor
    // body runs, so it would still be empty. It is set in BeginPlay, above Super.
}

void AMyHud::BeginPlay()
{
    // MUST precede Super::BeginPlay(). The component captures ApiKey when it builds its REST
    // client in its own BeginPlay, which Super dispatches. Set it later and ConnectUser still
    // succeeds while every REST call 401s with "api_key or app_id not provided".
    Client->ApiKey = ApiKey;
    Super::BeginPlay();

    const FUser User{UserId};
    Client->ConnectUser(
        User,
        UserToken,
        [WeakThis = TWeakObjectPtr<AMyHud>(this)](const FOwnUser& OwnUser)
        {
            if (!WeakThis.IsValid()) { return; }

            // One query with a filter, then Watch keeps it live over the websocket.
            // Without Watch, no events arrive and new messages never appear.
            const FFilter Filter = FFilter::In(TEXT("members"), {OwnUser.User->Id});
            WeakThis->Client->QueryChannels(
                Filter,
                {{EChannelSortField::LastMessageAt, ESortDirection::Descending}},
                EChannelFlags::State | EChannelFlags::Watch,
                {},   // FPaginationOptions
                [WeakThis](const TArray<UChatChannel*>& Channels)
                {
                    if (!WeakThis.IsValid()) { return; }
                    UE_LOG(LogTemp, Log, TEXT("Loaded %d channel(s)"), Channels.Num());
                    WeakThis->ShowChatUi();   // see widgets.md
                });
        });
}

void AMyHud::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    // Before Super: without this the socket only dies at GC, so in PIE the previous session's
    // connection outlives the session and the user stays online.
    if (Client) { Client->DisconnectUser(); }
    Super::EndPlay(EndPlayReason);
}
```

Then point the game mode at it - in C++ so the whole integration stays readable as text:

```cpp
AMyGameModeBase::AMyGameModeBase()
{
    HUDClass = AMyHud::StaticClass();
    DefaultPawnClass = nullptr;   // a chat app has no pawn to possess
}
```

### 4a. Seeding a channel from the client (optional)

`WatchChannel` is create-or-join-and-subscribe in one call, so it is idempotent and safe on every launch:

```cpp
FChannelProperties Props{TEXT("messaging"), TEXT("general")};
Props.SetMembers(TArray<FString>{UserId});
Props.SetName(TEXT("General"));
Client->WatchChannel(Props,
    [WeakThis = TWeakObjectPtr<AMyHud>(this)](UChatChannel* Channel)
    {
        if (!WeakThis.IsValid()) { return; }
        if (!Channel)
        {
            // A null channel usually means the channel type does not exist on the app, or this
            // user cannot create channels of that type. The callback fires either way - check it.
            UE_LOG(LogTemp, Error, TEXT("WatchChannel failed"));
            return;
        }
    });
```

Order matters and each step depends on the previous one:

```
ConnectUser  ->  (optional) WatchChannel to seed  ->  QueryChannels  ->  create + Setup the widget
```

### 4b. Production auth: `ITokenProvider`

A static token cannot be refreshed, so it dies when it expires. For anything real, connect with the provider overload against your own backend:

```cpp
class FMyBackendTokenProvider final : public ITokenProvider
{
public:
    // bRefresh is what lets the SDK re-fetch mid-session on expiry / auth error / reconnect.
    virtual FToken LoadToken(const FString& UserId, bool bRefresh = false) const override
    {
        // Call your authenticated endpoint here and return the JWT it issues.
    }
};

Client->ConnectUser(User, MakeUnique<FMyBackendTokenProvider>(), Callback);
```

`FConstantTokenProvider` wraps a fixed token when you genuinely have one. `ITokenProvider` is **not documented** upstream - the header is `Plugins/StreamChat/Source/Backend/TokenProvider/Public/ITokenProvider.h`; read it before generating an implementation.

### 4c. Blueprint wiring

If the project is Blueprint-only: add the **Stream Chat Client** component to a HUD Blueprint, set **API Key** in the component's Details panel (a default value on the component, so it is present before `BeginPlay`), then in the HUD's `Event BeginPlay` chain the latent nodes **Connect User** -> **Query Channels** -> your widget's **Setup** -> **Add to Viewport**. Latent nodes already sequence correctly through their exec pins, so do not add delays. The pagination and event-template APIs are unavailable here - say which parts of the request that blocks.

---

## 5. Chat UI

The client is now connected and channels are loaded. To put chat on screen, run [`widgets.md`](widgets.md) - do not improvise the widget wiring, because both of its main failure modes (instantiating the C++ class, or calling `Setup` after `AddToViewport`) render an empty widget with no error.

---

## 6. Verify before stopping

Compile and run, do not assume:

```bash
UE="/Users/Shared/Epic Games/UE_5.7"   # or resolve from LauncherInstalled.dat / $UE_ROOT

# Compile the editor target - needed once, and after any C++ change
"$UE/Engine/Build/BatchFiles/Mac/Build.sh" MyGameEditor Mac Development \
    -project="$PWD/MyGame.uproject" -waitmutex

# Run a map standalone, no editor UI. -unattended keeps it in the foreground on macOS.
"$UE/Engine/Binaries/Mac/UnrealEditor" "$PWD/MyGame.uproject" /Game/Main/Maps/Main \
    -game -windowed -ResX=430 -ResY=860 -unattended -log -stdout
```

(Windows: `Engine/Build/BatchFiles/Build.bat <Target> Win64 Development`. Linux: `Engine/Build/BatchFiles/Linux/Build.sh <Target> Linux Development`.)

A healthy first run logs roughly:

```
LogChatSocket: WebSocket configured with URL: wss://chat.stream-io-api.com/connect?...&api_key=<KEY>&...
LogChatSocket: WebSocket connected
LogTemp: Loaded 2 channel(s)
```

Check, in order:

- the plugin is enabled and the editor target compiles with `StreamChat` on the game module
- **`api_key=` in the websocket URL is non-empty** - the fastest proof the key landed before `BeginPlay`
- `ConnectUser`'s callback fires and `QueryChannels` returns a non-zero count (zero means the token user is a member of no channels - seed one)
- **zero `LogUMG` warnings** once a widget is on screen: every failed `BindWidget` logs there, so a clean `LogUMG` is real evidence the Stream widget tree built
- `DisconnectUser` runs on `EndPlay` - stop PIE and confirm the socket closes rather than lingering

For packaging and on-device runs, go to [`platforms.md`](platforms.md) - and note that a `Build.sh <Target> IOS` artifact is a compile check, **not** something you can install and run.

Then return to **Docs lookup** in [`SKILL.md`](SKILL.md) for each requested feature.
