# Stream React Native - non-negotiable rules

---

## Target SDK version and scope

Target **Stream Chat React Native**, **Stream Video React Native**, and **Stream Feeds React Native**.

- Follow the official docs for the current React Native New Architecture support matrix. When migration docs are stricter than the general New Architecture guide, use the stricter requirement.
- The bundled references assume the React Native **New Architecture**. Do not claim old-architecture support unless the docs for the selected package version explicitly say it is supported.
- This skill bundles Chat, Video, and Feeds. Do not implement or document React Native Moderation review UI from memory.

Use Stream `llms.txt` manifests as the docs authority. Start from [`references/DOCS.md`](references/DOCS.md), fetch the appropriate manifest, then fetch the selected markdown page before coding. Do not maintain or rely on hardcoded individual docs URLs. If a symbol must be verified in source, inspect the installed package in the target app's `node_modules` after install.

---

## Secrets and auth

Never put a Stream API secret in React Native code, Expo config, app config, native manifests, or chat. The client may receive the **API key** and a **user token**. The **API secret** stays server-side or inside the Stream CLI.

Default token model:

- Existing backend: use a backend-issued Stream token or token provider. **The backend must derive the Stream `user_id` from its own authenticated session (cookie / JWT / OAuth subject), not from a client-supplied query or body parameter.** Sending `user_id` to the token endpoint from the client is an impersonation bug - any signed-in user could mint a Stream token for any other user. The client wires a `tokenProvider` that re-hits the same authenticated endpoint on expiry. See [`sdk.md` > Auth model](sdk.md#auth-model) and the Production auth gate blueprint in [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md).
- Local dev/demo: use a CLI-generated token from [`credentials.md`](credentials.md). Gate any pasted-credential login form behind `__DEV__` or a feature flag so it cannot ship.
- User-managed: accept a pasted API key/token if the user chooses that path. Same dev-only caveat.

Never use `devToken()` for production. Never invent credentials. Never accept a client-supplied `user_id` on the token endpoint.

Prefer not to commit static user tokens. If the user wants a local-only demo and accepts a static token, keep the blast radius clear and avoid putting that token in shared docs or final summaries.

---

## Runtime lane ownership

Choose exactly one runtime lane from the project or request:

- **RN CLI:** Chat uses `stream-chat-react-native`; Video uses `@stream-io/video-react-native-sdk`; Feeds uses `@stream-io/feeds-react-native-sdk`.
- **Expo:** Chat uses `stream-chat-expo`; Video uses the same `@stream-io/video-react-native-sdk` package; Feeds uses the same `@stream-io/feeds-react-native-sdk` package (no separate Expo package for Video or Feeds).

Do not install both Chat packages (`stream-chat-react-native` and `stream-chat-expo`) unless the existing project already has a documented reason. Preserve the project's package manager (`npm`, `yarn`, `pnpm`) and navigation style.

For new app requests, default to Expo if the user did not choose a lane. Use RN CLI when the user asks for it or when native project constraints require it. Do not turn a non-empty unrelated directory into a new app without asking; create a child app directory instead when a name can be inferred.

---

## Package version and docs discipline

Before installing Stream Chat, Video, or Feeds RN packages:

1. Use [`references/DOCS.md`](references/DOCS.md) to fetch the appropriate manifest and the manifest-selected `Installation` markdown page (Chat: `https://getstream.io/chat/docs/sdk/react-native/llms.txt`; Video: `https://getstream.io/video/docs/react-native/llms.txt`; Feeds: `https://getstream.io/activity-feeds/docs/react-native/llms.txt`).
2. Run or consult `npm view <package> version dist-tags --json` for the selected package(s): `stream-chat-react-native`, `stream-chat-expo`, `@stream-io/video-react-native-sdk`, `@stream-io/feeds-react-native-sdk`.
3. Install `@latest` when the npm dist-tag matches the selected docs. If it does not, use the manifest-selected tag or exact version.

Before changing an existing Chat, Video, or Feeds UI, fetch the manifest-selected markdown page that matches the requested change. Choose the implementation path from the docs and the existing app: theme for style-only changes (Chat / Video; Feeds is headless and changes are made directly in the components you wrote), component overrides for UI slots (Chat / Video only), documented props/hooks for behavior, and optional native packages only for requested native capabilities.

**This rule also governs migration (Track M).** Never apply an SDK version upgrade from memory - fetch the matching upgrade / migration guide from the product manifest (or the known entry points in [`migrate.md`](migrate.md)) and apply *that*. Migrations are exactly where APIs move, native requirements change (e.g. the New Architecture becomes mandatory), and peer dependencies are added. Bump only the packages being upgraded, each to its own resolved version - Stream packages version independently. See [`migrate.md`](migrate.md).

**Matching a provided design is a decompose-and-plan-first task, not a theming afterthought.** When a Chat request carries a target appearance (screenshot, Figma, "look like \<app\>"), run [`references/design-matching.md`](references/design-matching.md) **before** writing UI code: decompose the reference region by region and plan every difference as theming / layout / functional, then verify region-by-region against the reference. Implement **every** region, the composer included; a region left at the SDK default is a FAIL, not a "known cosmetic gap." Report a region as unmatched only when it is genuinely impossible (say what + why), never because it is risky or more effort.

---

## Design-matching discipline (reasoning rules)

These are cross-cutting reasoning rules for matching a reference design. They catch the *class* of mistake a single fact never does — they generalize to regions not yet enumerated. They apply on top of [`references/design-matching.md`](references/design-matching.md), which carries the per-region facts and recipes. When a rule and a region-doc disagree, this file wins (last rule below).

- **A theme key that colours only *part* of a region means you hit an *inner* container.** A key that "kind of works" (paints a band around the controls, tints half the surface) is more dangerous than one that does nothing, because partial success doesn't trip the "go investigate" reflex. When styling looks partial, read the component's render tree and apply the value to the **outermost full-bleed `View`**, then verify the whole surface — sample the *margins around* a region, not just its foreground controls.
- **Regression adjacency — re-verify *every* facet of a region after *any* change.** Fixing one facet (structure / appearance / behaviour) routinely breaks a neighbour one layer down (rebuilding the picker breaks the attach button's look; restyling the button breaks its toggle behaviour). After each fix, re-check the region's other facets and both of its states before moving on — don't re-verify only the facet you just touched.
- **A theme-key / component-slot name is a hint, not a guarantee — confirm the target node in the render tree before using it.** Composer/message theme keys (`wrapper` vs `container` vs `inputBoxWrapper`, `MessageContent*` vs `MessageFooter`) do **not** map cleanly to "the thing you mean" by name. Two minutes reading the installed component's source beats a name-based guess that half-works.
- **A large custom build that parallels SDK infrastructure is a red flag — re-read the reference, don't proceed.** A knowledge-backed decision can still rest on a wrong premise (a misread screenshot), and knowing the API makes the wrong path *feel* informed so it never trips the "look this up" reflex. Before choosing a modal / host replacement / from-scratch surface over an SDK slot, **state the SDK's default structure for that region and diff it against the reference**. The SDK almost always has a slot; reinvention usually means you misread the reference.
- **No magic numbers — a size that represents a real thing anchors to that thing.** Sizes standing for a concrete thing (keyboard, safe area, header, tab bar) anchor to that thing (the SDK default or a measured reference value), never to "what feels roomy." When correcting an over/undershoot, reach for the simplest static approximation (e.g. an SDK default) *before* any runtime measurement hook — don't swing from an arbitrary number to an overwrought measured solution.
- **A green launch does not prove correctness.** Boot success proves nothing about a version-gated crash (surfaces on worklet/animation paths, not at boot), an unfilled background, or an off-by-a-safe-area size. Verify by the thing that's actually wrong — a version number, a sampled pixel, an on-device check — not by "it ran." Some defects (physical-scale sizing) only read wrong on a device, not on the roomy simulator window.
- **Idiomatic ≠ matching, in both directions.** Swapping in an SDK component for correct *behaviour* inherits its *appearance* (e.g. the SDK `AttachButton` is a bordered `type="outline"` button) — re-decompose the look after the swap. Re-customizing a slot for *appearance* must **reuse the SDK component's behaviour logic** (read its `onPress` and replicate it, including subtle branches) rather than hand-roll a lossy version.
- **In a device gallery, thumbnails are usually screenshots of *other apps* — content, not chrome.** A strip of app-like thumbnails with selection circles / duration badges / a grid is the **photo gallery**, not chat cards or an app switcher. Re-crop a region at full resolution before deciding its identity; don't let screenshot *content* invent a structural difference.
- **When two skill docs disagree, stop and reconcile before coding — RULES.md is the source of truth.** Do not silently follow the more specific or more design-focused file; surface the conflict and resolve it against this file first.
- **Confirm a prop's actual default in the installed source before relying on it.** A default you *assume* — or that guidance paraphrases in shorthand ("`0`/unset", "defaults to X") — isn't guaranteed to match the SDK: a prop destructured with **no default passes `undefined`**, not the value you expected (e.g. `Channel`'s `keyboardVerticalOffset`). This is about assumptions and loose shorthand, not distrusting the official docs — when behaviour hinges on a default, grep the component in `node_modules` for the pinned version instead of inferring it.
- **Verify every STATE, not every screen.** A region (composer, message row, picker) has multiple states — at-rest, typing, keyboard-up, voice-recording, edit, error/optimistic, empty/loading. Verifying the states that happen to render by default and skipping the ones you must *drive* is the recurring verification gap. Drive each state deliberately and put it on screen; "looks right in the states I screenshotted" ≠ correct.
- **When you override an accent/brand colour, override EVERY token that cascades from it — and treat any un-rendered state as hiding a stray default until proven otherwise.** Recolouring the common surfaces but leaving the SDK default in a less-common state (voice recording → `accentPrimary`/`chatWaveformBar`, edit, error, overlays, focus rings) is not a finished theme. The reference not *showing* a state is not permission to leave it half-themed — render it and sample it.
- **Fix the structure before the surface — never fake a structural property with a background fill.** If you're reaching for a hardcoded/sampled background colour to make a region "look right" (a translucent fill to fake a floating or blurred pill, a painted strip to fake an overlay), stop: a painted fill masking a structural difference is a defect, not a match. Map the difference to the SDK's structural mechanism first — a prop/flag/slot (e.g. `messageInputFloating` for a floating composer) — then theme the surface. Resolve the structural axis (floating, overlay, slot) *before* cosmetic polish (glass, exact colours), not after.
- **"The host is a direct import" ≠ "the layout is locked" — enumerate every context slot before concluding a region can't be restructured.** Before deciding a region isn't overridable, grep the parent component for **every** `useComponentsContext()` destructure and list all the slots it resolves; a host imported directly in `Channel` does not lock its children. (Example: `AttachmentPicker` resolves both `AttachmentPickerContent` and `AttachmentPickerSelectionBar` from context, so its internal layout — including a bottom bar — IS overridable.)

---

## Required peer setup

For Chat RN, required setup includes:

- `react-native-gesture-handler`
- `react-native-reanimated`
- `react-native-teleport`
- `react-native-svg`
- `@react-native-community/netinfo`
- `react-native-worklets` for RN CLI when Reanimated 4+ is used
- `expo-image-manipulator` for Expo image compression
- `expo-dev-client` for Expo apps

The Reanimated or Worklets Babel plugin must be the last Babel plugin. Wrap the app entry point in `GestureHandlerRootView`.

`react-native-teleport` is required because `OverlayProvider` uses it for portal-hosted UI.

**Reanimated / Worklets version floor (Expo SDK 57 — mandatory).** Expo SDK 57's bundled native-module pin is `react-native-reanimated@4.5.0` + `react-native-worklets@0.10.0` — a **known-crash pair** (the crash is on worklet/animation paths, not at boot, so a clean launch does not clear it — see *A green launch does not prove correctness* above). Require `react-native-reanimated` **≥ 4.5.1** and `react-native-worklets` **≥ 0.10.2** (verified-good pairing: `4.5.2` + `0.10.2`, which wants RN `0.83`–`0.86`), then rebuild native on both platforms. `npx expo install react-native-reanimated` **re-pins the crash version**, so the safe versions are baked into the install blocks in [`builder.md`](builder.md) and asserted in its §9 verify step — do not rely on remembering to bump. Confirm the current safe pairing against the reanimated release notes when the toolchain moves past SDK 57.

**Reanimated static feature flag (Reanimated 4 + Stream Chat — required).** Reanimated 4's `FORCE_REACT_RENDER_FOR_SETTLED_ANIMATIONS` defaults to `true` and is a **known regression source with Stream Chat** (bottom sheets, the message overlay, and context-menu animations). Set it to `false` in the **app-root `package.json`** — it is read at **pod-install time**, so it only takes effect after a native rebuild (`node_modules/react-native-reanimated/scripts/reanimated_utils.rb`):

```json
"reanimated": { "staticFeatureFlags": { "FORCE_REACT_RENDER_FOR_SETTLED_ANIMATIONS": false } }
```

Add it during setup (baked into [`builder.md`](builder.md)) and re-run pod install + rebuild native. For other Reanimated-4 animation regressions beyond this flag, fetch the manifest-selected docs (per *Package version and docs discipline*) rather than guessing.

For Video RN, required setup includes:

- `@stream-io/react-native-webrtc`
- `react-native-svg`
- `@react-native-community/netinfo`
- Expo only: `@config-plugins/react-native-webrtc`, `expo-build-properties`
- Android minSdk 24 (RN CLI: `android/build.gradle`; Expo: `expo-build-properties` plugin)
- Android Java 8 source / Java 11 target compatibility for the WebRTC module (RN CLI: `android/app/build.gradle` compileOptions)
- `NSCameraUsageDescription` and `NSMicrophoneUsageDescription` in `Info.plist`
- `CAMERA`, `RECORD_AUDIO`, `MODIFY_AUDIO_SETTINGS` (and `BLUETOOTH_CONNECT` if Bluetooth audio routing is wanted) in `AndroidManifest.xml`. **Foreground-service permissions are capability-owned** - the Expo config plugin only adds them when `androidKeepCallAlive` (background calls) or `enableScreenshare` is enabled, and you should mirror that on RN CLI. Don't declare `FOREGROUND_SERVICE*` for a plain foreground call - it over-broadens the manifest and creates Android 14 / Play policy review work for no reason.
- Expo only: add `@stream-io/video-react-native-sdk` and `@config-plugins/react-native-webrtc` to `app.json` plugins, then `npx expo prebuild --clean`

For Feeds RN, required setup includes:

- `@react-native-community/netinfo`

Feeds has no Reanimated, gesture-handler, SVG, or worklets requirement of its own. The SDK is headless. If you also wire Chat or Video, the peers from those products apply.

Both Chat and Video Expo apps use a dev-client/native-build lane. Feeds itself contains no native code beyond what `@react-native-community/netinfo` brings, so a plain Expo (managed or dev-client) workflow works for Feeds-only Expo apps - but if Chat or Video is also installed, the dev-client lane is required.

Optional native dependencies are capability-owned. Install them only for requested capabilities or when manifest-selected docs require them. The package matrices live in [`builder.md`](builder.md), [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md), [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md), and [`references/FEEDS-REACT-NATIVE.md`](references/FEEDS-REACT-NATIVE.md).

---

## Client lifetime and providers

**Chat:** Use `useCreateChatClient` for the normal Chat connection path. It creates a client, connects the user, returns `null` while connecting, and disconnects during cleanup. Never pass `null` to `<Chat client={...}>`.

Keep one stable `Chat` provider near the app root unless there is a strong reason to isolate contexts. Keep `OverlayProvider` stable and above navigation screens so long-press overlays, attachment picker, and image gallery can render above the active screen.

Do not create a `StreamChat` client:

- in a screen body
- in a component that remounts on every navigation
- per channel screen
- inside render-time factories or unstable callbacks

On sign-out, unmount or change the `useCreateChatClient` inputs. If offline support is enabled, reset the offline database before disconnecting.

**Video:** Always use `StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider, options? })` - never `new StreamVideoClient(...)`. Multiple instances break push notifications and call state. Create inside a `useEffect` keyed on `apiKey` and `user.id`, call `client.disconnectUser()` and clear state on cleanup. Pass the resulting client to `<StreamVideo client={...}>` mounted once near the app root; tearing it down restarts the WebSocket.

Use a `tokenProvider` (~4-hour tokens) for production. For ringing/push, pass the same options to `getOrCreateInstance` and `StreamVideoRN.setPushConfig` because the helper reuses cached instances and option mismatches break ringing.

Do not create a `StreamVideoClient`:

- with `new StreamVideoClient(...)` - always `getOrCreateInstance`
- in a screen body
- in a `useEffect` with empty deps inside a leaf component that remounts on navigation
- per call screen
- inside render-time factories or unstable callbacks

For `Call` lifetime: create inside a `useEffect`, `await call.join()` (or `getOrCreate()`), and on cleanup **guard the leave**: `if (call.state.callingState !== CallingState.LEFT) await call.leave()`. Dangling `Call` instances keep publishing audio/video and leak memory, but an unguarded second `leave()` (custom hangup + unmount, or React 18 strict-mode double-effect) throws `Cannot leave call that has already been left`. Hangup handlers should only navigate - `CallContent`'s default hangup already calls `leave()`.

A `Call` instance must be a **singleton per `(type, id)` pair**. The destination call screen mounts `<StreamCall call={call}>` and is the only place that calls `client.call(type, id, { reuseInstance: true })` for the active call. The `{ reuseInstance: true }` flag is required - the same `(type, id)` may already exist in the SDK's managed state (outgoing ring, ringing watcher, deep link, push), and without the flag the SDK constructs a duplicate that leaks SFU connections and breaks state. Every component inside `<StreamCall>` reads the call via `useCall()`; descendants must **not** call `client.call(...)` again to retrieve it.

Pass the call id and (when known) the call type through navigation params, not the `Call` object itself. Upstream screens (lobby, home) should not pre-create the `Call` - hand off the id/type and let the destination screen own the single mount.

`StreamVideoRN.setPushConfig({ ... })` requires a `createStreamVideoClient` callback - it is how the SDK rebuilds the client when waking from push. Always include it alongside any other config:

```ts
StreamVideoRN.setPushConfig({
  // Must return Promise<StreamVideoClient | undefined>
  createStreamVideoClient: async () =>
    StreamVideoClient.getOrCreateInstance({ apiKey, user, tokenProvider }),
  shouldRejectCallWhenBusy: true,
  // ios: { skipIncomingPushInForeground: true },
  // android: { skipIncomingPushInForeground: true },
});
```

For single-call concurrency, set `options: { rejectCallWhenBusy: true }` on `getOrCreateInstance` and add `shouldRejectCallWhenBusy: true` to `setPushConfig` (alongside `createStreamVideoClient`).

For app-owned in-foreground ringing UI (instead of CallKit/Telecom), set `skipIncomingPushInForeground: true` on the per-platform `ios` / `android` keys of `setPushConfig` (alongside `createStreamVideoClient`).

On iOS, call `StreamVideoReactNative.voipRegistration()` once from `didFinishLaunchingWithOptions` to register for VoIP push (Expo injects this call via the SDK config plugin).

**Non-ringing notifications** (`call.missed`, `call.notification`, `call.live_started` - the SDK's `NonRingingPushEvent` type) are entirely app-owned - the SDK does not display them or route taps. Register the device token explicitly via `client.addDevice(token, push_provider, push_provider_name)`; on iOS this is a separate APN token because the ringing VoIP token is PushKit-only.

**Feeds:** Use `useCreateFeedsClient({ apiKey, tokenOrProvider, userData })` for the normal Feeds connection path. It creates a `FeedsClient`, connects the user, returns `undefined` while connecting, and disconnects on cleanup. Never pass `undefined` to `<StreamFeeds client={...}>`.

Keep one stable `StreamFeeds` provider near the app root, above any screens that read Feeds state. For sharing the user's `user` and `timeline` feeds across screens, wrap the navigator in an `OwnFeedsContextProvider` that creates both feeds once and establishes the self-follow (`timeline.follow(userFeed.feed)`) so own posts appear on the timeline. Do not pass `Feed` objects through navigation params - read them from this context on the destination screen. Pass `activityId` (string) through navigation params, never the full `ActivityResponse`; on activity-details screens, create a live handle with `client.activityWithStateUpdates(id)` and call `.dispose()` on unmount.

Do not create a `FeedsClient`:

- in a screen body
- in a component that remounts on every navigation
- per feed screen
- inside render-time factories or unstable callbacks

On sign-out, unmount the `useCreateFeedsClient` host (or change its inputs) and call `client.disconnectUser()` if you have direct access to the instance.

---

## Navigation and overlay discipline

When using React Navigation or Expo Router:

- **Chat:** Place `OverlayProvider` above the navigation screens. With React Navigation, prefer `OverlayProvider` above `NavigationContainer`. Keep `Chat` high enough that screen transitions do not reconnect the client. Pass channel CIDs or ids through navigation params, not `Channel` instances. Recreate the `Channel` instance from `useChatContext().client` on the destination screen. **`keyboardVerticalOffset`/`topInset` on `<Channel>` offset for chrome that sits *above* the Channel and pushes its top down — a native navigation header, or (rarely) a custom header rendered as a *sibling above* `<Channel>`.** In that case set **both** to that header's height (equal values — `topInset` is what the attachment picker uses to compute its bottom-sheet snap point; without it the sheet clamps short). A custom header rendered *inside* `<Channel>` (the common floating in-screen-header pattern) has nothing above the Channel to offset, so pass both **explicitly as `0`** (`keyboardVerticalOffset={0} topInset={0}`). **Do not rely on omitting them:** in the installed SDK, `Channel` defaults `topInset` to `0` but **destructures `keyboardVerticalOffset` with no default**, so omitting it passes `undefined`, not `0` (confirm in the pinned source — *documented/assumed behaviour is not the SDK default*, see Design-matching discipline). A non-zero value over-compensates the keyboard-avoiding view and mis-computes the picker snap. **Default to an explicit `0`;** set a non-zero value only when a native header is present. **Verify by focusing the input so the real software keyboard rises** — programmatic `setText` does NOT raise the keyboard, so it never exercises this prop — with the picker also opened. `bottomInset` stays opt-in (only for a tab bar that owns the bottom safe-area).
- **Video:** Place `StreamVideo` above `NavigationContainer` (or above the Expo Router root layout) so the client survives screen transitions. Pass the call id (and call type when not the default) through navigation params, not `Call` instances. The destination call screen mounts `<StreamCall>` after calling `client.call(type, id, { reuseInstance: true })` once; descendants read via `useCall()`. Other screens/components must not call `client.call(...)` to obtain the same instance.

For Chat threads, keep thread state explicit. When a thread screen is open, pass the same `thread` value to the main `Channel` and render the thread screen with `threadList`.

---

## Expo Router SDK 56+ — no React Navigation

Expo Router on SDK 56+ ships its own navigation runtime and **refuses to bundle alongside `@react-navigation/*`**. Metro halts with:

> As of SDK 56, expo-router is no longer compatible with react-navigation.

Rules:

- Do not install `@react-navigation/native`, `@react-navigation/native-stack`, `@react-navigation/elements`, or any other `@react-navigation/*` package in an Expo Router SDK 56+ app, even transitively (the bundler fails before runtime). If one is already there (often pulled in to satisfy a `useHeaderHeight` import), `npm uninstall` it.
- The Chat blueprint pattern that calls `useHeaderHeight()` from `@react-navigation/elements` only applies to **RN CLI** and **Expo Router SDK ≤ 55**. For Expo Router SDK 56+, compute the header offset from `Platform.OS` + the top safe-area inset (see [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) > Channel Screen).
- For RN CLI apps where React Navigation is the navigation stack, the existing blueprint stands — there is no Expo Router conflict to manage.
- Detect the lane via the `EXPO_SDK` line in the project-signals probe in [`SKILL.md`](SKILL.md). Expo SDK 56+ goes through the SDK-56 recipe; everything else uses the original blueprint.

---

## Safe areas and Android edge-to-edge

Every screen the skill ships must respect safe areas on iOS and edge-to-edge layout on Android. Apply these rules without exception:

- Use **`react-native-safe-area-context`** for all inset handling: `SafeAreaProvider` at the app root (required, not optional), `SafeAreaView` from this package for full-screen wrappers, and `useSafeAreaInsets()` for custom padding. Never import `SafeAreaView` from `"react-native"`.
- **Toolchain caveat (RN 0.85 + Expo 56 + new architecture):** `react-native-safe-area-context@5.7` `SafeAreaView` wraps a native `NativeSafeAreaView` that appears to no-op on this toolchain - the JS render returns but the inset never actually applies, leaving content under the notch / home indicator. The `useSafeAreaInsets()` hook reads from the same context through a different code path and works correctly. When in doubt on RN 0.85+, prefer `View` + `useSafeAreaInsets()` + explicit `paddingTop` / `paddingBottom` over `<SafeAreaView edges={...}>`. Add `paddingBottom: insets.bottom + N` to any `FlatList`'s `contentContainerStyle` that sits under a native tab bar so the last items clear it.
- **Android edge-to-edge is mandatory.** Pick the branch that matches the app:
  - **Expo**: set `"edgeToEdgeEnabled": true` under `android` in `app.json` (default-on from Expo SDK 54).
  - **RN CLI 0.81+**: set `edgeToEdgeEnabled=true` in `android/gradle.properties`. The RN Gradle plugin handles the rest - no `react-native-edge-to-edge` install, no `styles.xml` edit.
  - **Older RN CLI**: install `react-native-edge-to-edge` and inherit a `Theme.EdgeToEdge` variant in `android/app/src/main/res/values/styles.xml`.
  iOS is already edge-to-edge by default and needs no extra config.
- **Status bar / nav bar** styling: Expo apps use `expo-status-bar` (and optionally `expo-navigation-bar`), both ship in every Expo template - no extra install. RN CLI apps use `<SystemBars style="auto" />` from `react-native-edge-to-edge`. Both APIs are equivalent on Expo SDK 54+ (Expo wrappers delegate to `SystemBars`). Do not call deprecated `StatusBar` APIs from `react-native` when edge-to-edge is on. For deeper nav-bar control (per-screen styling, hide / show, immersive mode) see the live [Safe area insets cookbook page](https://getstream.io/video/docs/react-native/ui-cookbook/safe-area-insets.md).
- **For Stream Video screens**, the SDK does not infer insets on its own. Read them with `useSafeAreaInsets()` and bridge into `<StreamVideo style={theme}>` (or a scoped `<StreamTheme>`) where `theme.variants.insets = { top, right, bottom, left }`. `CallContent`, `RingingCallContent`, `HostLivestream`, `ViewerLivestream`, and participant views consume those theme insets.
- **Anti-pattern**: once `variants.insets` is wired, do **not** wrap `CallContent`, `RingingCallContent`, `HostLivestream`, or `ViewerLivestream` in a `SafeAreaView` - they already pad themselves from the theme and a wrapper produces visible double padding. Same rule applies to a custom `CallControls` slot: don't re-read `useSafeAreaInsets()` and add `paddingBottom` if the theme already carries `insets.bottom`.
- **For Stream Chat screens**, `<Channel>` handles its own insets - do not wrap `MessageComposer` or `MessageList` in `SafeAreaView` to fix spacing. Add `topInset` / `bottomInset` props on `<Channel>` only when a specific layout issue proves they are needed.

---

## Offline support

Offline support is opt-in.

- Install `@op-engineering/op-sqlite` only when requested.
- Pass `enableOfflineSupport` to `Chat`.
- Expo apps already use a dev-client/native-build lane. Expo Go is not a supported target for this skill.
- Access to threads in offline mode is not implemented in the referenced docs.
- On sign-out, run `chatClient.offlineDb.resetDB()` before `disconnectUser()` to avoid cross-user data leaks.

For offline-first boot, read the offline section in [`sdk.md`](sdk.md) before coding. The docs require starting `connectUser` before rendering Chat components but not blocking the UI on the promise.

---

## Chat + Video interop

A single RN app may run both `stream-chat-react-native` (or `stream-chat-expo`) and `@stream-io/video-react-native-sdk` together.

- Build both clients with the same API key.
- Both products can share the same user token if both are enabled for the API key.
- Mount providers in any nesting order, but **nest** them rather than placing them as siblings, and keep both above the navigator. `OverlayProvider` + `<Chat>` (Chat) and `<StreamVideo>` (Video) operate on independent contexts and do not collide.
- Disconnect both clients on sign-out before creating new ones for a different user.
- For interop-specific guidance (calling from inside a chat channel, attaching a chat thread to a call), fetch the manifest-selected Chat Integration page: `https://getstream.io/video/docs/react-native/advanced/chat-with-video.md`.

---

## Reference discipline

Load only the React Native files that match the request and product:

- [`references/DOCS.md`](references/DOCS.md) for `llms.txt` manifests and docs lookup routing (Chat, Video, and Feeds)
- [`sdk.md`](sdk.md) for shared RN/Expo, auth, provider, navigation, offline, and sign-out patterns
- Chat: [`references/CHAT-REACT-NATIVE.md`](references/CHAT-REACT-NATIVE.md) (setup, gotchas) and [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md) (screen/component structure)
- Video: [`references/VIDEO-REACT-NATIVE.md`](references/VIDEO-REACT-NATIVE.md) (setup, gotchas) and [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md) (screen/component structure)
- Feeds: [`references/FEEDS-REACT-NATIVE.md`](references/FEEDS-REACT-NATIVE.md) (setup, gotchas) and [`references/FEEDS-REACT-NATIVE-blueprints.md`](references/FEEDS-REACT-NATIVE-blueprints.md) (screen/component structure)

### Blueprints are mandatory, on every turn

Before writing or editing **any** Stream Chat, Stream Video, or Stream Feeds React Native screen, provider, hook usage, navigation handler, thread / comments flow, theming override, offline flow, ringing handler, call control, participant tile, activity row, composer, follow button, or component customization, you **must** open the matching section of the corresponding blueprints file:

- Chat work -> [`references/CHAT-REACT-NATIVE-blueprints.md`](references/CHAT-REACT-NATIVE-blueprints.md)
- Video work -> [`references/VIDEO-REACT-NATIVE-blueprints.md`](references/VIDEO-REACT-NATIVE-blueprints.md)
- Feeds work -> [`references/FEEDS-REACT-NATIVE-blueprints.md`](references/FEEDS-REACT-NATIVE-blueprints.md)

This applies on **every turn**, not just the first time the skill is invoked in a session. Follow-up requests like *"add navigation to the channel screen"*, *"open a channel on tap"*, *"add a button to start a call"*, *"customize the call controls"*, *"theme the call screen"*, *"add a ringing screen"*, *"add a comments modal"*, *"wire the follow button"*, *"render the notification feed"*, *"attach an image to a post"*, or *"register the device for push"* count as new screen work and require a fresh blueprint read.

Use the **Request -> Blueprint section** table at the top of each blueprints file. If no section matches, say so before improvising. Do not rely on a blueprint read earlier in the session; re-read the relevant section before each Stream screen edit.

---

## CLI and shell discipline

Credentials and requested demo data use the `getstream` binary. If the binary is missing, ask the user to install it from https://getstream.io and wait - never run an install script or introduce a new installer flow.

For `getstream api` calls, follow [`../stream/RULES.md`](../stream/RULES.md) > CLI safety: confirm endpoints with `getstream api -h` before running them, and only run mutating demo-data calls after the user explicitly asks for demo data.

Do not read or print `.env` files. Do not use `bash -ce` in probes.
