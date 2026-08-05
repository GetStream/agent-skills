# Stream Unreal - platform config, packaging, and deploy

Run this when the request involves building for a device, packaging, shipping, or diagnosing "it works in the editor but not on my phone". The plugin supports **Win64, macOS, Linux, Android, iOS**.

The mobile config below is **load-bearing, not polish**. v2.0.0's release notes say iOS and Android were "both unusable in packaged builds" before the fix - and the fixes are almost entirely config. A new project starting from blank gets none of them, and there is no docs page telling you to copy them. So an agent that packages a mobile chat app must write them.

---

## 1. The build-vs-package distinction (get this right first)

These two commands are for different jobs, and confusing them costs the most time:

| Command | Produces | Use for |
|---|---|---|
| `Build.sh <Target> IOS Development` | signed, **content-free** `.app` | proving the SDK + integration compile and link for `arm64` |
| `RunUAT.sh BuildCookRun ... -build -cook -stage -package -pak` | deployable `.app` / `.ipa` | anything you actually run on a device |

`Build.sh` **compiles and links only**. It never cooks or stages, so the bundle has no cooked assets and no `.uproject`. It is signed, it has an `Info.plist`, an icon, and an `embedded.mobileprovision`, and `devicectl device install app` will happily accept it. It then crashes on launch:

```
Message: Failed to open descriptor file ../../../MyGame/MyGame.uproject
App terminated due to signal 11.
```

**Rule: never describe a `Build.sh IOS` artifact as deployable.** When the user asks to run on a device, go straight to `BuildCookRun`.

This is also where [`widgets.md`](widgets.md) Step 5's `DirectoriesToAlwaysCook` earns its keep: the compile-only path never cooks, so a missing cook directive is **invisible** there - it surfaces as a missing widget class only once you package, which is exactly when it is most expensive to find.

---

## 1b. Every packaged build needs `n.VerifyPeer=True`, on every platform

Before any per-platform config: without this, a **packaged** build cannot reach Stream at all. The editor
hides it completely, so this only appears once you package.

```ini
; Config/DefaultEngine.ini
[/Script/Engine.NetworkSettings]
n.VerifyPeer=True
```

The chat client talks to Stream over a secure WebSocket, so it needs CA root certificates to verify
Stream's certificate. The engine ships them at `Engine/Content/Certificates/ThirdParty/cacert.pem`, and
UAT stages that file into packaged builds **only if this key is present** - `CopyBuildToStagingDirectory`
reads it with `GetBool`, which writes `false` into its out-parameter when the key is absent, so its
`bStageSSLCertificates = true` initializer is dead code. Nothing in `BaseEngine.ini` sets a default, so
every project starts in the broken state, and the editor masks it by reading the engine's copy straight
from disk.

The symptom is an app that launches fine and then never connects, retrying forever:

```
LogWebSockets: Warning: Lws(Error): SSL error: unable to get local issuer certificate
```

Setting it does **not** make the app less strict: at runtime the value is only applied when the key exists
(`CurlHttpManager.cpp` guards its `GetBool` with an `if`), so an unset key already meant "verify the peer".
Setting it explicitly just makes packaging agree with the runtime.

Do **not** work around this by copying `cacert.pem` into project content and staging it with
`+DirectoriesToAlwaysStageAsNonUFS=(Path="Certificates")`. That bypasses the gate rather than setting it,
duplicates a 208 KB engine file, and uses NonUFS for no reason - the certificates are read through UE's
pak-aware file APIs, since the WebSockets module gets them via
`FSslModule::Get().GetCertificateManager().AddCertificatesToSslContext()`.

## 2. iOS config

Four settings across two files decide whether the packaged app is usable at all. Each one is verified against what the SDK's own sample ships.

### `Config/IOS/IOSEngine.ini`

```ini
[/Script/Engine.UserInterfaceSettings]
; The engine's default UIScaleCurve has its first key at a viewport height of 2160, so a phone falls
; below the curve and clamps to scale 1.0 - a desktop-authored layout ends up far too small to read
; or tap. Scaling the application up here beats rewriting the curve, which affects desktop too.
ApplicationScale=1.750000

[SystemSettings]
; Every avatar sits in a retainer box, which renders its subtree to its own render target each frame.
; On a handset that exhausts Slate's draw buffer pool, after which the game thread blocks forever in
; GetDrawBuffer - the app appears to freeze a few frames in. (Observed: frozen on frame 31 with the
; same warning logged 443k times.) Retained rendering is a desktop optimisation.
Slate.EnableRetainedRendering=0
```

### `Config/IOS/IOSInput.ini` - and it must be this file

```ini
[/Script/Engine.InputSettings]
; On touch platforms the engine creates a virtual joystick that consumes touches across the whole
; screen, so UMG never sees a tap or a scroll and the chat UI looks frozen. Nothing to drive with a
; joystick in a chat app.
DefaultTouchInterface=None
; Permanent viewport capture is for a game that owns the pointer. Uncaptured input is what lets
; Slate route touches to widgets.
DefaultViewportMouseCaptureMode=NoCapture
DefaultViewportMouseLockMode=DoNotLock
```

> **The silent one.** `UInputSettings` is `config=Input`, so these keys **only** work in `IOSInput.ini`. Putting them in `IOSEngine.ini` is a **no-op that logs nothing** - and it is easy to get wrong because every other iOS override does live in `IOSEngine.ini`.

For an in-game chat overlay rather than a chat-only app, `DefaultTouchInterface=None` may not be what you want (the game may need the joystick). In that case keep the joystick and instead set the input mode so Slate gets first refusal on touches over the chat widget - and say explicitly that this is a trade-off you made, not a default.

### `Config/DefaultEngine.ini`

```ini
[/Script/IOSRuntimeSettings.IOSRuntimeSettings]
bSupportsPortraitOrientation=True
bSupportsLandscapeLeftOrientation=False
bSupportsLandscapeRightOrientation=False
MinimumiOSVersion=IOS_16
; Chat needs a real text field, not Unreal's fullscreen virtual keyboard overlay, which covers the
; conversation while typing.
bUseIntegratedKeyboard=True
```

Drop the orientation lines if the app is not portrait-only. `bUseIntegratedKeyboard` is a chat-specific recommendation rather than something the sample ships - state it as such, and it is worth testing both ways with the user.

Note what `BundleIdentifier` in this section does **not** do - see 3.

---

## 3. iOS signing: the documented setting is the wrong one on UE 5.5+

UE's iOS toolchain has **no `-NoCodeSign` path** - the final `.app` finalize always goes through Xcode signing. Compiling and linking the whole SDK for `arm64` succeeds with no signing setup at all; only the finalize step needs a team.

**The trap:** every guide, and UE's own `IOSRuntimeSettings`, tells you to set

```ini
[/Script/IOSRuntimeSettings.IOSRuntimeSettings]
bAutomaticSigning=True
IOSTeamID=ABCDE12345
```

On UE 5.7 that is **silently ignored**. Those keys feed the *legacy* Xcode generator (`XcodeProjectLegacy.cs`). The modern generator (`XcodeProject.cs`, default since ~5.5) reads a different section entirely, and writes `DEVELOPMENT_TEAM` into a generated **xcconfig** rather than the `.pbxproj`:

```ini
; This is the one that works.
[/Script/MacTargetPlatform.XcodeProjectSettings]
bUseAutomaticCodeSigning=True
CodeSigningTeam=ABCDE12345
CodeSigningPrefix=com.yourcompany
```

Set only `IOSTeamID` and you get `DEVELOPMENT_TEAM =` (empty) in `Intermediate/ProjectFilesIOS/XcconfigsIOS/<Target>.xcconfig`, and the build fails with the misleading *"Select a development team in the Signing & Capabilities editor"* - misleading because there is no Xcode project you are meant to edit; it is regenerated every build.

Two more consequences of the modern path:

- **`BundleIdentifier` under `IOSRuntimeSettings` does not control the bundle ID.** The xcconfig sets `PRODUCT_BUNDLE_IDENTIFIER = $(UE_SIGNING_PREFIX).$(UE_PRODUCT_NAME_STRIPPED)`, so the real id is `CodeSigningPrefix` + product name (`io.getstream.unreal` + `StreamChatDemo` -> `io.getstream.unreal.StreamChatDemo`), regardless of a lowercase `BundleIdentifier` set elsewhere.
- **Debug it by grepping the generated xcconfig, not the pbxproj:**
  ```bash
  grep -n "DEVELOPMENT_TEAM\|CODE_SIGN_STYLE\|PRODUCT_BUNDLE_IDENTIFIER" \
    Intermediate/ProjectFilesIOS/XcconfigsIOS/<Target>.xcconfig
  ```

With the correct section, UBT passes `-allowProvisioningUpdates` and Xcode creates or refreshes a wildcard *"iOS Team Provisioning Profile: \*"* automatically, giving a signed bundle at `Binaries/IOS/<Target>.app` with an `embedded.mobileprovision` and the expected `TeamIdentifier`.

**Rule: emit the `XcodeProjectSettings` section (optionally both, for legacy compatibility), and stop and ask for the team ID rather than guessing.** Automatic signing registers an App ID on the user's Apple Developer account - that is not a reversible local change, so it needs their say-so.

For CI or a shared machine, manual signing is the alternative: the SDK sample uses `MobileProvision=build_pp.mobileprovision` under `IOSRuntimeSettings` with a checked-in profile. Offer it if the user does not want automatic registration.

---

## 4. Android config

The same class of problem applies - a desktop-authored UMG layout on a handset - so mirror the iOS settings in the Android equivalents:

```ini
; Config/Android/AndroidEngine.ini
[/Script/Engine.UserInterfaceSettings]
ApplicationScale=1.750000

[SystemSettings]
Slate.EnableRetainedRendering=0
```

```ini
; Config/Android/AndroidInput.ini   - same config=Input rule as iOS: it must be this file
[/Script/Engine.InputSettings]
DefaultTouchInterface=None
DefaultViewportMouseCaptureMode=NoCapture
DefaultViewportMouseLockMode=DoNotLock
```

```ini
; Config/DefaultEngine.ini
[/Script/AndroidRuntimeSettings.AndroidRuntimeSettings]
PackageName=com.yourcompany.yourapp
bBuildForArm64=True
bBuildForArmV7=False
Orientation=Portrait
```

Android also needs the NDK/SDK set up in **Edit > Project Settings > Platforms > Android SDK**; UE ships a `SetupAndroid` script under `Engine/Extras/Android/` for that. Tune `ApplicationScale` against a real device rather than assuming 1.75 - it was derived on a phone-sized iOS viewport.

These Android values are the reasoned mirror of the verified iOS ones rather than settings observed in the sample. Say that when you emit them, and verify on device.

---

## 5. Desktop (Win64 / macOS / Linux)

Nothing special. The default `UIScaleCurve` and retained rendering are fine on desktop - **do not** copy the mobile overrides into `DefaultEngine.ini`, or you scale up the desktop UI too and lose an optimisation that desktop actually wants. That is why the mobile settings live in per-platform files.

The only cross-platform requirement is the cook directive in [`widgets.md`](widgets.md) Step 5, if the integration loads widgets by path.

---

## 6. Commands

Resolve the engine root first. `$UE_ROOT` if set; otherwise Epic's `LauncherInstalled.dat`:

```bash
UE=$(python3 - <<'PY'
import json, os, re
m = os.path.expanduser("~/Library/Application Support/Epic/UnrealEngineLauncher/LauncherInstalled.dat")
d = json.load(open(m))
ue = [((int(x.group(1)), int(x.group(2))), i["InstallLocation"])
      for i in d.get("InstallationList", [])
      for x in [re.fullmatch(r"UE_(\d+)\.(\d+)", i.get("AppName", ""))] if x]
print(sorted(ue)[-1][1] if ue else "")
PY
)
echo "$UE"    # e.g. /Users/Shared/Epic Games/UE_5.8
```

(Windows: `C:\ProgramData\Epic\UnrealEngineLauncher\LauncherInstalled.dat`. Default install paths are `/Users/Shared/Epic Games/UE_5.x` and `C:\Program Files\Epic Games\UE_5.x`.)

```bash
# Compile the editor target - needed once, and after any C++ change
"$UE/Engine/Build/BatchFiles/Mac/Build.sh" MyGameEditor Mac Development \
    -project="$PWD/MyGame.uproject" -waitmutex

# iOS COMPILE CHECK ONLY - produces a content-free .app that crashes on launch (see 1)
"$UE/Engine/Build/BatchFiles/Mac/Build.sh" MyGame IOS Development \
    -project="$PWD/MyGame.uproject" -waitmutex

# iOS build you can actually deploy
"$UE/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
    -project="$PWD/MyGame.uproject" \
    -platform=IOS -clientconfig=Development \
    -build -cook -stage -package -pak -nocompileeditor

# Android build you can actually deploy
"$UE/Engine/Build/BatchFiles/RunUAT.sh" BuildCookRun \
    -project="$PWD/MyGame.uproject" \
    -platform=Android -clientconfig=Development \
    -build -cook -stage -package -pak -nocompileeditor

# Run a map standalone, no editor UI. -unattended matters on macOS - see below.
"$UE/Engine/Binaries/Mac/UnrealEditor" "$PWD/MyGame.uproject" /Game/Main/Maps/Main \
    -game -windowed -ResX=430 -ResY=860 -unattended -log -stdout
```

On Windows swap `BatchFiles/Mac/Build.sh` -> `BatchFiles/Build.bat` and `RunUAT.sh` -> `RunUAT.bat`; on Linux use `BatchFiles/Linux/Build.sh`.

**macOS editor trap:** `UnrealEditor` re-execs itself into `UnrealEditor.app/Contents/MacOS/UnrealEditor` and **detaches**, so the launching shell exits ~1 and any stdout redirect captures only the stub. Pass `-unattended` (with `-log -stdout`) to keep it in the foreground and capture the real log - otherwise a wrapper script reports a failure that did not happen.

**Xcode range:** each engine version accepts only a range of Xcode versions (Epic's constraint). `Platform Mac is not a valid platform to build` means Xcode is outside it; the range is in `Engine/Config/Apple/Apple_SDK.json`.

### In the SDK repo specifically

If the user is working inside a clone of `stream-chat-unreal` (which is itself the sample project), it drives everything through `just`, and a clone needs **Git LFS** first ([`RULES.md`](RULES.md)):

```bash
git lfs install && git lfs pull
just build-editor        # compile
just demo                # Team Chat sample
just run in-game-chat    # team-chat | in-game-chat | jumpy-lion | tutorial
just test                # automation tests
just engine              # print the engine it resolved
just set-engine 5.8      # swap .uproject/.uplugin for the other engine version
just format              # clang-format with the version CI pins
```

---

## 7. Deploying to an iOS device without `ios-deploy`

`ios-deploy` is commonly cited and frequently not installed. Xcode 15+ ships `devicectl`, which needs nothing extra:

```bash
xcrun devicectl list devices                                    # look for "available (paired)"
xcrun devicectl device install app --device <UDID> <Path>.app
xcrun devicectl device process launch --device <UDID> --console <bundle-id>
```

Two gotchas:

- **UE does not log to stdout on iOS.** `--console` shows the Objective-C wrapper's `NSLog` output and the crash reason, but **not** `LogStreamChat*` / `LogChatSocket` lines. It is still the fastest way to see *why* a launch failed. For UE's own log, pull it from the app data container:
  ```bash
  xcrun devicectl device info files --device <UDID> \
      --domain-type appDataContainer --domain-identifier <bundle-id> --username mobile
  ```
- **A development-signed build installs only on devices listed in the profile.** Check before wondering why install failed:
  ```bash
  security cms -D -i <App>.app/embedded.mobileprovision | plutil -extract ProvisionedDevices raw -
  ```
  A team wildcard profile (`TEAMID.*`, "iOS Team Provisioning Profile: \*") usually already lists every registered team device.

Android equivalent: `adb install -r <path>.apk` and `adb logcat -s UE` (UE does log to logcat, so `LogChatSocket` lines are visible there - a genuine advantage over iOS when debugging the connection).

---

## 8. Push notifications

The SDK implements **device registration** only - `AddDevice(DeviceId, EPushProvider)`, `RemoveDevice(DeviceId)`, `ListDevices(Callback)`. Everything else (creating the provider on your Stream app, the APNs `.p8` / FCM service account, the payload template) is server-side setup, and the platform token itself comes from the OS, not from Stream.

- A device registers only **after** the user connects. Registering earlier is a no-op.
- The APNs auth key / FCM credentials go to **Stream** (Dashboard or CLI), **never** into the app bundle or git.
- The provider name you configure on the Stream app must match what the client passes.
- **Real device only** - push never fires on a simulator.
- Getting the platform device token in Unreal is engine-level work (`UGameplayStatics`/platform delegates or an ancillary plugin), not something the Stream plugin does for you. Say so rather than implying `AddDevice` obtains the token itself.

Route the server-side config to `https://getstream.io/chat/docs/unreal/push-introduction.md` and `.../push-devices.md` (which does carry Unreal code), and see [`docs-map.md`](docs-map.md).

---

## 9. Ship checklist

- correct release archive for the engine version, plugin enabled, editor target compiles
- **`n.VerifyPeer=True` in `DefaultEngine.ini`** - without it a packaged build never connects (see 1b)
- API key present **before** `BeginPlay` (non-empty `api_key=` in the websocket URL)
- no hardcoded production token; `ITokenProvider` wired if tokens expire
- `DirectoriesToAlwaysCook` present if any widget is loaded by path
- per-platform config written to the **per-platform** files (input keys in `*Input.ini`)
- iOS: `XcodeProjectSettings` signing section, team id confirmed **by the user**
- packaged (not just compiled) and launched on a real device
- `DisconnectUser` on teardown; zero `LogUMG` warnings; a message from another client arrives live
