# Stream React (web) - non-negotiable rules

React / Next.js-specific rules for the `stream-react` skill. These **layer on top of** the
cross-cutting rules in [`../stream/RULES.md`](../stream/RULES.md) - read that file once per
session too. Where the two files state the same rule differently (e.g. Strict mode
protection, Package manager), **this file wins for React work** - the cross-cutting file
also serves the framework-agnostic `stream-builder` pack. Each rule below is stated once;
other files reference this file - do not duplicate these rules inline.

---

## Env vars are server-side only

**The secret is server-side only** - never in the client bundle, never `NEXT_PUBLIC`.
`getstream env` writes the **public** API key with the framework's client prefix
(`NEXT_PUBLIC_STREAM_API_KEY`) plus the server-only `STREAM_API_SECRET` to `.env.local`. The
client may read `NEXT_PUBLIC_STREAM_API_KEY` directly or receive `apiKey` from the
`/api/token` response; either way the token is minted server-side (with the secret) and
returned by `/api/token`. (The core "never read/edit `.env`" rule lives in
[`../stream/RULES.md`](../stream/RULES.md) > Secrets.)

- Narrow `searchParams.get()` (returns `string | null`) with guards before passing to SDK methods.

## Login Screen first

Every app opens with a **Login Screen** as its root page (`app/page.tsx`). The app never
auto-connects or hardcodes a user. Credentials (token, apiKey, userId) live in **React
state** - not localStorage - so each browser tab can operate as an independent user. Layout
and behavior details: [`builder-ui.md`](builder-ui.md) > Login Screen.

## Strict mode protection

```ts
const [client, setClient] = useState<StreamVideoClient>();
useEffect(() => {
  const tokenProvider = () => fetchToken(userId);   // defined INSIDE the effect
  const c = new StreamVideoClient({ apiKey, user: { id: userId, name }, tokenProvider });
  setClient(c);
  return () => { c.disconnectUser().catch(console.error); setClient(undefined); };
}, [apiKey, userId, name]);
```

The client constructor is synchronous, so this effect needs cleanup but not a timer or mounted flag. The canonical full snippet (client + call join + render gate) lives in [`references/VIDEO.md`](references/VIDEO.md) > Client Patterns - replicas elsewhere must match it. Async call/feed setup effects must use a local `mounted` flag and cleanup; use `setTimeout` only where the relevant product reference requires it.

**Do NOT use `useRef` as a "run once" guard** in setup effects (e.g. `const initRef = useRef(false); if (initRef.current) return; initRef.current = true;`). `useRef` persists across strict mode's unmount->remount cycle - if you set `ref.current = true` on the first mount, it stays `true` after cleanup, and the second mount skips initialization entirely. This prohibition is about effects **with cleanup/teardown** (client, call, and feed connection setup). **Carve-out:** a one-shot idempotent fetch with **no cleanup** whose result lives in SDK state - e.g. the initial `loadNextPage()` for `useActivityComments` - may use a ref guard: the first fetch's result survives the remount in feed state, so skipping the second invocation is correct (a `mounted` flag would not prevent the double-fetch there).

- Client-side Chat: `useCreateChatClient()` handles strict mode internally - don't use `getInstance()` (singletons break strict mode).
- Client-side Feeds: `useCreateFeedsClient()` handles strict mode internally - no manual pattern needed for connection. But `feed.getOrCreate()` must still use the `setTimeout` + `mounted` guard.
- Server-side: `StreamChat.getInstance(apiKey, apiSecret)` is fine (singleton OK).

## Base UI (not Radix)

Shadcn components use `@base-ui/react`, NOT `@radix-ui`. Key differences:
- **Never use `asChild`** - it does not exist in Base UI. Trigger components render children directly.
- Style triggers by passing `className` directly to `<DropdownMenuTrigger>`, `<PopoverTrigger>`, etc.
- Do NOT wrap triggers with `<Button>` - style the trigger element itself.

## Theme

Use whatever theme Shadcn generates. Do not modify `globals.css` after init - no dark mode overrides, no custom variable blocks. The scaffold includes `next-themes` with a `ThemeProvider` (system default, class-based toggle) - use it as-is.

**Design-matching exception:** when a screenshot / Figma dictates the palette, match it through the sanctioned channels - the shadcn `--preset` and Stream's documented `str-chat` theming variables / `<Channel>` theming - not ad-hoc `globals.css` edits. See [`references/design-matching.md`](references/design-matching.md) > Palette through the sanctioned channels.

## Reference authority

**Prebuilt-component-first.** Stream's React SDKs ship rich prebuilt components, and the React
docs/cookbooks are built around customizing them. Default to that path:

- **Chat:** compose `<Chat>` / `<ChannelList>` / `<Channel>` / `<Window>` / `<MessageList>` / `<MessageComposer>` / `<Thread>` (v14 uses `MessageComposer`, not `MessageInput`).
- **Video:** compose `<StreamVideo>` / `<StreamCall>` + a prebuilt layout (`SpeakerLayout`, `PaginatedGridLayout`, livestream layout) / `ParticipantView` / `CallControls`.
- **Feeds:** headless - there are no prebuilt UI components; always build from the hooks (`useFeedActivities`, `useActivityComments`, ...).

**Customize via the documented hooks/props** (e.g. `<MessageList Message={Custom} />`,
`useChannelStateContext()`, `useMessageContext()`, `useCallStateHooks()`, `<Channel>` theming) -
fetch the matching docs page first (see Docs-first below).

**Writing your OWN component for a prebuilt region triggers [`references/custom-ui.md`](references/custom-ui.md) - load it BEFORE you build.** This is the predicate, and it is easy to get wrong:

- **Passing props / theme** to a prebuilt component (a cookbook recipe's prop, `<Channel>` theme tokens) -> just fetch the page.
- **Writing your own component/markup for a region** - a custom message row / `MessageUI`, a custom composer, a custom channel preview or header, a custom call layout - **load `custom-ui.md` first, then fetch the page.** This holds **even when you wire it via the documented `Message=` / `WithComponents` prop**, and it is **not** limited to a "fully bespoke app".

Why: replacing a prebuilt region means you inherit every sub-feature it rendered. `custom-ui.md` carries the **completion contract** (reproduce-or-mark-`N/A`: attachments, reactions, quoted replies, receipts, threads, edited/deleted, grouping) that stops a custom row from silently dropping them. Still docs-first either way.

**Reference files are the source of truth for the components they document** - which prebuilt
component to use, its props, SDK wiring, and property paths. Do not generate Stream SDK code from
training data.

**Order of authority** (highest first): the matching **live docs page** (component reference,
cookbook, or advanced topic) > the bundled **reference / blueprint** for the common-path
component > anything else. Never training-data recall. The bundled blueprints cover the common
path; when the request is a customization, the live docs page **overrides** both the blueprint
and memory - fetch it.

## Docs-first for cookbook / advanced features

**Before implementing any feature that matches a UI component, UI Cookbook, or Advanced Guide topic, fetch the matching Stream docs page first.** [`references/docs-map.md`](references/docs-map.md) holds the keyword -> page map and the protocol. The bundled `references/*-blueprints.md` cover the common path; component-reference and cookbook/advanced topics - the prebuilt component props, typing indicator, custom message UI, message actions, reactions, message composer / input UI, channel header, emoji picker, autocomplete, link previews, AI integrations, advanced search, multiple lists, infinite scroll, channel read state, online status, location sharing, blocking users, message reminders, notifications, attachment previews, audio playback, date/time formatting, SDK state management, dialog management, TypeScript custom data types, chat + video integration, call layouts, PiP, network quality, livestream watching, recording, broadcasting - change often and **must** be built from the current page, not memory.

**This rule also governs migration (Track M).** Never apply an SDK upgrade from memory - fetch the matching release / upgrade guide from the index in [`references/docs-map.md`](references/docs-map.md) (or [`migrate.md`](migrate.md)) and apply *that*.

**Flow:** match a trigger -> `WebFetch` the `.md` URL from [`references/docs-map.md`](references/docs-map.md) -> read it this turn -> implement to match.

**Hard gate on fetch failure.** If the page does not load, hand the lookup to the `stream-docs` skill. If **neither** the page nor `stream-docs` resolves the API, **stop and tell the user** - report that you could not confirm the current API and ask how to proceed. **Do not implement the feature from memory.** A guess that happens to compile is still a guess.

**Violating the letter of this rule is violating its spirit.** Fetching "later", fetching "only if it breaks", or building first and reconciling against the docs afterward are all violations.

| Excuse | Reality |
|--------|---------|
| "I already know the typing-indicator / reactions API" | Knowing the concept != the current API. One fetch confirms it. |
| "The blueprint already covers this" | Blueprints are the common path; the cookbook page is the customization you were actually asked for. |
| "I'll just hand-build it instead of using the prebuilt component" | Prebuilt-first is the rule. Hand-built markup is only for explicit bespoke-UI requests - and still docs-first. |
| "The user is in a hurry" | One `WebFetch` is not the bottleneck. Shipping the wrong API is. |
| "It's almost a trigger but not exactly" | Almost = fetch. Default to fetching when unsure. |
| "WebFetch failed, I'll just wire it from memory" | Failure means escalate to `stream-docs`, or stop and ask - never memory. |
| "I'll build it now and check the docs after" | That encodes the wrong pattern first. Fetch before writing, not after. |
| "It's just a version bump, I know what changed" | Migrations are exactly where APIs move. Fetch the release guide first. |

**Red flags - STOP and fetch the page (or hand to `stream-docs`):**
- About to write a component / cookbook / advanced feature without having fetched its page this turn.
- Reaching for a remembered prop / hook name instead of the documented one.
- Hand-building markup when a prebuilt component exists and the user did not ask for bespoke UI.
- Telling yourself the blueprint or memory is "good enough" for a customization request.
- Applying a version upgrade without having read the matching release guide.
- Implementing after a failed fetch instead of escalating to `stream-docs` or asking the user.

## Package manager

- **Track A scaffold:** always use `npm`, never bun, and pass `--legacy-peer-deps` when installing Stream packages.
- **Track E enhance / Track M migrate:** preserve the existing project's package manager and lockfile. For npm projects, pass `--legacy-peer-deps` for Stream packages.

## Builder phase order (React)

The generic onboarding + phase-order discipline lives in [`../stream/RULES.md`](../stream/RULES.md) > Onboarding & phase order. React-specific additions:

- Do not load `references/*.md` until the user names the product(s).
- Do not load [`builder-ui.md`](builder-ui.md) before Step 4.
- Shadcn/ui is always installed during Step 3 - never skip. **stream-react does not install third-party frontend skills** (no install step). If such packs (`frontend-design`, `vercel-react-best-practices`, `web-design-guidelines`) are already present in the session, use them for generic UI polish only - Stream references stay authoritative for SDK wiring. (The consent-to-install rule in [`../stream/RULES.md`](../stream/RULES.md) > Builder phase order is for `stream-builder`, which retains that step; this file wins for React.)

## Moderation is Dashboard-only

**Never build a moderation review queue, review panel, or flagged-item UI in the app.** Moderation review always happens in the [Stream Dashboard](https://beta.dashboard.getstream.io). The app's role is limited to:
- **CLI setup** during scaffold (blocklists, automod config via [`references/MODERATION.md`](references/MODERATION.md) Setup)
- **End-user actions** (report, block, mute) if the product needs them
- `references/MODERATION-blueprints.md` bundles **end-user actions only** (Report Modal, Block/Mute Controls, Blocked Users List); review-queue / flagged-item / auto-mod blueprints are deliberately absent - do **not** recreate them

---

## Inherited cross-cutting rules

The following live in [`../stream/RULES.md`](../stream/RULES.md) and apply here unchanged - read them there, do not restate:

- **Peer skills** - Glob/install/invoke procedure for sibling packs.
- **Secrets** - never Read/Edit `.env`; let the CLI own it; `.gitignore` before any `.env` write.
- **No auto-seeding** - the `/api/token` route upserts only the requesting user; no demo users/content unless asked.
- **CLI safety** - no guessing endpoints; confirm with `getstream api -h` and read the CLI's output.
- **Onboarding** - run `getstream init` (auth + org/app + credentials) before build/integrate work.
- **Shell discipline** - no `bash -ce`/`set -e` in probes; browser sign-in (`getstream init` / `getstream login`) stays its own invocation.
- **Cross-track follow-ups** - offer, do not auto-execute, the natural next action across tracks.
- **Sandboxed / blocked shell fallback** - print commands for the user and continue read-only.
