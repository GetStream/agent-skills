# Stream Swift - push setup (Chat push + Video VoIP / CallKit)

Triggered by requests like "add push notifications for chat" or "ringing should wake the app on an incoming call". Goal: a **seamless, mostly-automated** setup. One APNs auth key (`.p8`) powers everything - regular alert push and VoIP - so there is one manual step (Apple has no key-creation CLI) and the rest is CLI + generated code.

Obey [`RULES.md`](RULES.md) throughout - especially: the `.p8` goes to Stream via the CLI, never into the app bundle.

---

## Step 0: Scope it

| User wants | Mechanism | Providers to create | Client work |
|---|---|---|---|
| Chat push (message while backgrounded) | APNs alert push | one named `apn` | permission + device register |
| Video ringing (incoming call wakes app) | VoIP push + CallKit | one named `voip` | PushKit + CallKitAdapter |
| A calling + messaging app (both) | both of the above | `apn` **and** `voip` (same key) | both |

Also decide whether a **Notification Service Extension** is needed (Step 5) - ask or infer from the use case.

---

## Step 1: APNs auth key (.p8) - one-time manual step

Apple provides **no CLI/API to generate an APNs auth key** (the App Store Connect API does not expose key creation; fastlane cannot either), so this single step is manual. If the user already has a `.p8`, skip to Step 2.

In the Apple Developer portal: **Certificates, Identifiers & Profiles -> Keys -> + -> enable "Apple Push Notifications service (APNs)" -> Register -> Download** the `.p8` (downloadable **once**). Capture three values:

- **Key ID** - 10 chars, shown on the key.
- **Team ID** - 10 chars, on the Membership page.
- **Bundle ID** - the app's bundle identifier (this is the APNs `topic`).

A single token `.p8` enables **both** alert and VoIP push - no separate VoIP certificate needed. (Legacy alternative: a VoIP Services Certificate `.p12` via `apn_p12_cert` - only if the user insists; the token path below is simpler and preferred.)

---

## Step 2: Create the Stream push provider(s) via CLI

The provider stores the key **server-side**; the SDK never sees it. Use `UpsertPushProvider` (POST `/api/v2/push_providers`). Build the body with `jq --rawfile` so the `.p8` newlines survive, and pipe over stdin so the key is never pasted inline:

```bash
# Regular APNs provider (Chat push + Video alert push)
jq -n --rawfile key /path/AuthKey_<KEYID>.p8 \
  '{push_provider:{type:"apn",name:"apn",apn_auth_type:"token",apn_auth_key:$key,apn_key_id:"<KEYID>",apn_team_id:"<TEAMID>",apn_topic:"<BUNDLE_ID>",apn_development:true}}' \
  | getstream api UpsertPushProvider --request @-
```

```bash
# VoIP provider (only for ringing video calls; same key, name "voip")
jq -n --rawfile key /path/AuthKey_<KEYID>.p8 \
  '{push_provider:{type:"apn",name:"voip",apn_auth_type:"token",apn_auth_key:$key,apn_key_id:"<KEYID>",apn_team_id:"<TEAMID>",apn_topic:"<BUNDLE_ID>",apn_development:true}}' \
  | getstream api UpsertPushProvider --request @-
```

Notes:

- `apn_development:true` targets the **sandbox** (debug builds run from Xcode). Set `false` for TestFlight / App Store builds - flip it per environment, or keep separate dev/prod apps.
- Preview the request without sending: append `--dry-run`.
- Confirm: `getstream api ListPushProviders`. Remove one: `getstream api DeletePushProvider --type apn --name voip`.
- If the user prefers a file over stdin, write the JSON to a temp file and use `--request @/tmp/apn.json`, then delete it. Never echo the `.p8` contents into the chat.

Exact field schema (from the live API): `type`, `name`, `apn_auth_type` (`token` | `certificate`), `apn_auth_key`, `apn_key_id`, `apn_team_id`, `apn_topic`, `apn_development`, `apn_host`, `apn_p12_cert`.

---

## Step 3: Capabilities + entitlements (Xcode -> Signing & Capabilities)

- **Chat push:** add the **Push Notifications** capability.
- **Video VoIP / CallKit:** add **Push Notifications** + **Background Modes** with **Voice over IP**, **Remote notifications**, and **Background processing** checked.

---

## Step 4: Client registration code

Fetch the exact, current code from the docs (routes in [`docs-map.md`](docs-map.md)) and apply it to the project's lifecycle. The essentials:

### Chat (alert push) - `.../sdk/ios/client/push-notifications.md`

Request authorization after connecting the user, then register the device in the app delegate:

```swift
UNUserNotificationCenter.current()
    .requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
        guard granted else { return }
        DispatchQueue.main.async { UIApplication.shared.registerForRemoteNotifications() }
    }

func application(_ application: UIApplication,
                 didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
    guard chatClient.currentUserId != nil else { return }
    chatClient.currentUserController().addDevice(.apn(token: deviceToken))   // multi-bundle: .apn(token:providerName: "apn")
}
```

### Video (VoIP + CallKit) - `.../advanced/incoming-calls/push-notifications.md` + `.../advanced/incoming-calls/callkit-integration.md`

Provider names here **must match** the dashboard names from Step 2 (`apn` / `voip`):

```swift
let notificationsConfig = PushNotificationsConfig(
    pushProviderInfo: PushProviderInfo(name: "apn", pushProvider: .apn),
    voipPushProviderInfo: PushProviderInfo(name: "voip", pushProvider: .apn)
)
// pass to the client: StreamVideo(apiKey:, user:, token:, pushNotificationsConfig: notificationsConfig, ...)

@Injected(\.callKitAdapter) var callKitAdapter
callKitAdapter.streamVideo = streamVideo
callKitAdapter.registerForIncomingCalls()   // call after login, e.g. in onAppear
```

Register the VoIP token as it changes (observe `callKitPushNotificationAdapter.$deviceToken` -> `streamVideo.setVoipDevice(id:)`, and `deleteDevice(id:)` on the previous token). The `CallKitAdapter` reports incoming calls to CallKit automatically from the VoIP push - no manual `CXProvider` wiring. For "Recents" deep-links, add the optional Intents Extension (`INStartCallIntent`) per the CallKit page.

---

## Step 5: Notification customizations (optional) - decide, do not default

A **Notification Service Extension (NSE)** modifies the notification before it shows (Chat only):

- **Add an NSE when** the app wants real message previews: sender name + avatar, decrypted text, accurate unread/mute handling. Use `ChatRemoteNotificationHandler`, an App Group, and set `config.applicationGroupIdentifier` so the extension and app share data. Route: the NSE section of the Chat push page.
- **Skip the NSE when** a generic alert ("You have a new message") is enough, or for **ringing video calls** (VoIP + CallKit present the call UI directly - no NSE).

If unclear, ask one question:

> Do you want rich notifications (sender, message text, avatar), or is a simple "new message" alert enough? Rich previews need a Notification Service Extension.

---

## Step 6: Verify

- `getstream api ListPushProviders` -> the provider(s) exist with the right `name` and `apn_topic`.
- `getstream api CheckPush ...` tests the push config server-side; or do an end-to-end test: a real message from a second user (chat) / a ringing call from a second user (video).
- **Real device required** - APNs and especially VoIP do **not** work on the simulator.
- A device token registers only **after** connecting the user (chat) / initializing `StreamVideo` with the config (video). If push is silent, confirm the device appears via `getstream api ListDevices` and that `apn_development` matches the build (sandbox vs production).
