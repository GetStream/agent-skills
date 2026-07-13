# Builder - UI shell and theme (Step 4)

Load when executing **Step 4** (after scaffold). Rules: [`RULES.md`](RULES.md) (login screen first, theme, reference authority).

> **Reference-design override.** If the request carries a screenshot / Figma / "make it look like X", the **reference's frame wins over the generic shell defined here** (App Header, sidebar, shell geometry). Reproduce the reference's frame per [`references/design-matching.md`](references/design-matching.md) - **remove in-app chrome the reference doesn't show** (a bare phone-chat reference has no app top-bar and no chat-list sidebar) and **fill the viewport** (no fixed-width chat strip beside empty background) - then apply the region + theming guidance here within it. The Login Screen stays as the auth gate unless the reference itself is the full app.

### Step 4: Generate ALL code files
Write every file sequentially. Follow the UI Guidelines below for all visual styling. See **RULES.md > Reference authority** - reference files are the only source of truth for SDK wiring. Before writing each component, load the prebuilt path in the relevant `references/<Product>-blueprints.md`; fetch the matching live page from [`references/docs-map.md`](references/docs-map.md) for any customization, and load [`references/custom-ui.md`](references/custom-ui.md) (the completion contract) first when you write your own component for a region - even one, even via `Message=` / `WithComponents`.

#### Login Screen (required for every app - RULES.md > Login Screen first)

Centered card on a neutral background. No sidebar, no nav - just the login form.

**Layout (top to bottom, all centered inside the card):**
- App icon / logo
- App name (use-case label)
- Single `username` input (required, full card width)
- `Continue` primary button (no arrow glyph in label - see UI Guidelines > Button labels)
- Hint text below the button, in `text-muted-foreground text-sm`: "Open this URL in another tab with a different username to test multi-user features."

**Behavior:**
- Username input is **required**
- On submit: `GET /api/token?user_id={username}` -> store credentials in **React state** (not localStorage - each tab must be independent)
- After successful token fetch, render the main app UI (state gate, not redirect)
- App name / use-case label above the input

#### App Header (default shell - omit when a reference design doesn't show it)

Once logged in, the default shell shows a persistent header bar (but see the **Reference-design override** above - a screenshot that has no app top-bar means you drop this):

- **Left:** App name (derived from use case)
- **Right:** Avatar circle (initial letter) + username + "Switch User" button
- "Switch User" clears all token/client state and returns to the Login Screen
- The header sits above all product UI (chat sidebar, video player, feed, etc.)

This ensures the developer always knows which user they are operating as.

---

## UI Guidelines

### Stack
- Next.js 16, Tailwind v4, TypeScript (match scaffold defaults).
- **Shadcn/ui with Base UI** - scaffolded via `shadcn init -t next -b base -p <preset>` (preset chosen in SKILL.md Step 1b - the user's own preset, or a random fallback; applied in Task A). Use Shadcn components (`Button`, `Input`, `Textarea`, `Card`, etc.) for all standard UI. Add more via `npx shadcn@latest add <component>` as needed.
- **Icons:** Use whichever icon package the scaffold installed (check `package.json`). If none present, `lucide-react` is installed during Step 3 Task C. Standard PascalCase imports:
  `import { Heart, Send, Bookmark, MoreHorizontal } from "lucide-react"`. If the project uses a different icon package (e.g. `@phosphor-icons/react`), use that one instead - do not mix icon packages.
- Tailwind utility classes for custom styling beyond Shadcn components - never inline styles.
- **Theme:** RULES.md > Theme - `next-themes` with system default (class-based dark mode, scaffolded automatically).
- `-webkit-font-smoothing: antialiased` on html (set by scaffold).

### Theme

Use whatever `globals.css` Shadcn generates. Do not add custom variables, custom themes, or dark mode overrides. The scaffold includes `next-themes` with `ThemeProvider` (system default, class-based toggle) - use it as-is.

### Design

Use Shadcn components, Tailwind utilities, and - if frontend skill packs are already available in the session - the frontend skills to build a polished UI. No further opinions; use your best judgement. Stream references provide structure and wiring; frontend skills (when present) provide generic design guidance.

### Button labels

**Never put arrow characters in button text** - no ASCII arrow sequences (like `->`, `>>`) and no unicode arrow glyphs (any codepoint that renders as an arrow or chevron) in the label. If a button needs an arrow visually, use a proper icon component (e.g. `lucide-react`'s `<ArrowRight />`, `<ChevronRight />`) rendered alongside the label. Otherwise, leave the label plain (e.g. `Continue`, not `Continue ->`).

### Stream SDK CSS & Providers

- **Chat:** Import the Chat CSS ([`sdk.md`](sdk.md) > CSS imports for the path + version variants). Use `useCreateChatClient` from `stream-chat-react` to instantiate. Match theme: `useTheme()` -> `str-chat__theme-dark` or `str-chat__theme-light` to `<Chat>`.
- **Video:** Import `@stream-io/video-react-sdk/dist/css/styles.css`. Instantiate `StreamVideoClient` with the canonical `useState` + `useEffect` pattern (NOT `useMemo` - see `references/VIDEO.md`).
- **Feeds:** No CSS import - headless SDK. Wrap app in `<StreamFeeds client={client}>`, then per-feed in `<StreamFeed feed={feed}>`. Use `useCreateFeedsClient()` for client creation - **gate rendering on `client !== null`** (returns `null` until connected). Call `feed.getOrCreate({ watch: true })` inside `setTimeout(50ms)` + `mounted` guard (strict mode protection) before passing to `<StreamFeed>`. See `references/FEEDS.md` for complete patterns.

**Provider hierarchy:** mount **all** Stream providers - `<Chat>`, `<StreamVideo>`, `<StreamFeeds>` - once at AppShell, in any order. Per-screen components render `<Channel>`, `<StreamCall>`, or `<StreamFeed>` from the existing root providers. **Never re-instantiate Stream clients per screen** - the cleanup of one screen's effect will disconnect a client another screen is still using. For multi-product apps, see [`references/CROSS-PRODUCT.md`](references/CROSS-PRODUCT.md) for the full skeleton.

**Layout / sizing (Stream regions fill their parent).** The prebuilt regions must **grow to fill the container you put them in** - the SDK's default `str-chat` CSS can otherwise cap the **channel list at a fixed width** (you may see ~30% / ~288px) and leave the message list or header not filling. Own the sizing with your wrapper:
- **No fixed-size components - fluid by default.** Never author a layout container at a bare fixed CSS size (`width: 320px`, `height: 600px`): every region, list, bar, and background is `w-full h-full` inside its column and grows with its container - the chat background, the channel-list background, everything. When the design calls for a proportioned pane (a sidebar rail), put the constraint on the **wrapper** as a flex-basis / percentage / `clamp()` (e.g. `flex: 0 0 clamp(280px, 25vw, 400px)`) and let everything inside fill 100% of that wrapper. Fixed px belongs to **intrinsic details** (avatar diameter, icon size, radius, gap, padding) - never to a layout container; a container authored at a bare fixed px matches one viewport and breaks at every other. (One exception: a deliberate phone-frame shell in a mobile-reference match - the frame itself is the design; everything inside it still fills the frame.)
- A **flex row**: the channel-list column gets its proportion (a flex-basis / `clamp()` rail, or `flex-1` to fill); the `<Channel>` / `<Window>` column is `flex-1 min-w-0` (the `min-w-0` defeats flexbox `min-width: auto`, which otherwise blocks `<MessageList>` from growing/shrinking to its column).
- A **height chain**: root the height at the AppShell (`h-dvh` / `h-full`) so `<ChannelList>` and `<MessageList>` fill vertically instead of collapsing.
- **Bottom-anchor + full-height background.** A chat conversation bottom-anchors: with few messages the list pins content to the bottom (against the composer), it does not top-anchor and leave a gap. And any **wallpaper / background** (doodle pattern, tint) must be painted on the **full-height scroll container**, not the content wrapper - otherwise it stops where the messages stop and leaves a blank band above the composer. The prebuilt `<MessageList>` already bottom-fills; a custom message-list wrapper must not break it.
- Each region `w-full h-full` inside its column - the **wrapper decides the width**, not the component's own default; `<ChannelHeader>` (or a custom header) spans the full width of the main pane.
- If the SDK default still caps the channel-list width, override it through the documented `str-chat` sizing variable (confirm the current name on the Theming page - do not guess it) or a wrapper width utility. Do not ship the ~288px default when full width is wanted.
- **`<Channel>` / `<Window>` render intermediate DOM nodes you cannot `className`** (`.str-chat__channel`, `.str-chat__main-panel`). Putting `flex-1 min-w-0` on *your* wrapper `<div>` and on the inner column is not enough if a Stream node sits between them and doesn't grow - size those nodes with a `str-chat` CSS override, not just your wrapper divs.
- **Multi-pane (conversation + details/thread) case:** when `<Channel>` wraps *both* a conversation column **and** a details or thread sibling inside a flex **row**, `.str-chat__channel` is itself the flex-row child that must fill `<main>` - give it `display:flex; flex:1 1 0%; min-width:0` in CSS (it won't grow on its own). A flex-**column** parent hides this bug (column children stretch to full width automatically), so verifying in a column layout while shipping a row layout passes falsely - **verify in the row layout you ship** (see [`references/design-matching.md`](references/design-matching.md) > verify against the shipped layout).
- **Thread panel defaults to `width: 100%`** (`.str-chat__thread-container` / `.str-chat__thread`), so an open thread *takes over the pane* instead of sitting beside the conversation. For a right-sidebar thread (desktop), constrain it in CSS via a flex-basis on the wrapper (`flex: 0 0 clamp(<min>, <fraction>, <max>)` - not a bare fixed `width`) and keep the conversation column `flex-1` - the same "an SDK region fills/collapses unless you own the sizing" gotcha as the channel-list ~288px cap. Letting it fall back to full-pane below your desktop breakpoint is a reasonable mobile/tablet pattern. **Its open layout is only visible once the thread is opened - drive it in the verify loop** ([`references/design-matching.md`](references/design-matching.md) 6a/6c).

### Moderation

**Never build moderation review UI in the app** (RULES.md > Moderation is Dashboard-only). All review happens in the [Stream Dashboard](https://beta.dashboard.getstream.io). The app's role is **CLI setup only** (blocklists, automod config in Step 3).

### Reference Blueprints

See RULES.md > Reference authority. Load `references/<Product>.md` (header) for setup + gotchas, and `references/<Product>-blueprints.md` for the prebuilt provider tree + props. For fully bespoke UI on the low-level client, see [`references/custom-ui.md`](references/custom-ui.md). Load only the product(s) relevant to the current use case.

**Prebuilt-first default (Chat + Video).** Build the common path with the SDK's prebuilt React components - Chat: `<Chat>` / `<ChannelList>` / `<Channel>` / `<Window>` / `<MessageList>` / `<MessageComposer>` / `<Thread>` (v14 uses `MessageComposer`, not `MessageInput`); Video: `<StreamVideo>` / `<StreamCall>` / `SpeakerLayout` / `PaginatedGridLayout` / `ParticipantView` / `CallControls`. Customize via the documented hooks/props - register custom UI through `<WithComponents overrides={{...}}>` or pass a per-list `<MessageList Message={Custom} />`; read state with `useChannelStateContext()` / `useCallStateHooks()`) - fetch the matching cookbook page first (RULES.md > Docs-first). Drop to fully hand-built markup **only** when the user explicitly wants bespoke UI; [`references/custom-ui.md`](references/custom-ui.md) carries the prebuilt-vs-bespoke decision + the headless context-hook map for that case. Feeds is headless (no prebuilt UI) - always build from its hooks.
