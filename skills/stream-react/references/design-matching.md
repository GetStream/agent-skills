# Stream React (web) - matching a reference design (screenshot / Figma / "make it look like X")

Run this whenever the request carries a **target appearance** - an attached screenshot, a Figma
frame, a whiteboard sketch, or "make it look like WhatsApp / Slack / Linear / <app>". A reference
design is a **checklist of regions, not a color tweak**: every rail, bar, row, tile, and card is a
thing to reproduce, and most differ from Stream's defaults *structurally*, not just by color.

**The thesis of this whole file:** a match is **claimed only from a rendered screenshot captured
this round and compared against the reference** - never from the code you wrote, never from your
classes, never from eyeballing the running app (however late or careful). "I implemented every region"
is a plan, not a match.

**Implement EVERY region - the composer is first-class.** Do not deliver a partial match with the
rest labelled "known cosmetic gap": a region left at the SDK default is a FAIL, not a footnote. Only
genuine impossibility is a reason to skip, and then you say exactly what and why (see The verify loop
> Exit honestly).

Division of labor - this file owns the *procedure*; it does not restate what it references:
- **Customize-vs-bespoke decision + the per-region completion contract:** [`custom-ui.md`](custom-ui.md).
- **Every URL / page name:** [`docs-map.md`](docs-map.md) - cite row names here, never raw URLs.
- **Non-negotiables** (no backend seeding, docs-first, palette channels, prebuilt-first, work in
  batches): [`../RULES.md`](../RULES.md) and [`../../stream/RULES.md`](../../stream/RULES.md).

**Work in batches** (the loop economics): decompose ALL regions -> ground ALL names -> build ALL
regions -> then **one capture per verify round, never one per tweak**. A full match is many regions;
batching the fixes and capturing once per round is what keeps it fast.

The pipeline is six steps: **Classify -> Spec -> Route -> Ground -> Build -> Verify loop.**

---

## Step 1: Classify the reference

Before decomposing, classify what you were handed - it sets the match standard and the verify
standard.

| Tier | Input looks like | Match standard | Verify standard |
|---|---|---|---|
| **Pixel** | An app screenshot or a Figma PNG export | Measured: sampled hex values, measured dimensions, exact type | Full verify loop (every spec row measured against a this-round capture) |
| **Lo-fi** | A sketch, wireframe, or whiteboard photo | Structural: the right regions, present, in the right hierarchy | Verify loop checks presence + layout rows only; palette comes from the sanctioned theme channels, never sampled from pencil |
| **Figma link, no exports** | A `figma.com/...` URL with no attached images | **Stop and ask for PNG exports, one per frame** | n/a until you have images |

**Figma links: stop and ask.** You cannot authenticate to Figma and you must never guess a design
from a URL, a file name, or an app's name. Ask for a PNG export per frame, then classify as Pixel.

**The capture requirement is identical for Pixel and Lo-fi** - Step 6 (a browser screenshot taken this
round) is mandatory for both; only *what you measure* differs (Lo-fi drops color / type sampling, never
the capture). Presence and layout are confirmed from the this-round capture and the probe `missing`
flags, never from reading your own markup. **When unsure which tier, treat it as Pixel.**

**Multiple screenshots** = one spec per screen, but **one shared token table**: sample the palette
and type roles once and reuse them across screens (they are one app). The verify loop then captures
and diffs each screen separately.

**Derive the viewport** (it is a spec field - the loop captures at exactly this size):

| Reference shows | Viewport (CSS px) |
|---|---|
| Portrait ~9:19.5, a status bar / notch | Mobile `390 x 844` |
| ~3:4, no phone chrome | Tablet `820 x 1180` |
| Window chrome, multi-column rails | Desktop `1440 x 900` |
| A known Figma frame | That frame's exact declared size |

**Scale rule:** `scale = reference-image-px-width / viewport-CSS-width`. Divide every dimension you
measure off the image by `scale` before it enters the spec (a 132px avatar on a 3x mobile shot is
44 CSS px). Do not enter raw image pixels as CSS pixels.

**Mobile reference, web deliverable - decide the framing up front.** The reference is almost always a
mobile-app screenshot, but you are shipping a web app - the single highest-leverage decision in these
builds. Settle it with the user before building: either **(a) reproduce the mobile layout at phone
width** (often inside a phone-frame element on the page), or **(b) adapt to the app's desktop-web
layout** (e.g. WhatsApp Web's two-pane shell). Pick per the request; when it is genuinely ambiguous,
ask. If you choose the phone-frame approach, also decide **modal containment**: Stream's fullscreen
image / gallery viewer renders to the document root and will **escape a phone frame** (fill the whole
browser window) unless you scope it - a common web-porting artifact.

---

## Step 2: Write the spec

Write the spec down, per screen - do not hold it in your head and do not code from an impression. The
spec has two halves: the **attributes** (what to measure) and the **taxonomy** (naming the Stream
concept behind every visual signal). The taxonomy is where regions get silently dropped, so it is the
centerpiece.

### Attributes to record per region

- **Regions / layout:** name every column, bar, rail, tile, and card. A region you do not name is a
  region you will silently drop.
- **Colors - sample, do not guess:** the hex of each sub-part (chrome, list bg, incoming vs outgoing
  bubble, text, muted text, accent, unread badge, presence dot). A "weird line" between two regions is
  usually a **color seam** (two backgrounds meeting), not a divider element. A background may be a
  **texture / gradient / image**, not a flat fill.
- **Type - per text role:** family, size, **weight** (its own axis - match it separately), line
  height, for author / body / timestamp / unread each.
- **Dimensions - measure, do not eyeball:** rail width, avatar size, bubble radius + padding, row
  gap, header height. Read pixels off the image and divide by `scale`; never invent round numbers
  (16 / 24 / 32).
- **Exact text & glyphs (not just layout):** transcribe verbatim the text the design shows - the
  composer **placeholder string** (e.g. `Message`, not the SDK default `Send a message`), button
  labels, empty-state copy - and match the **exact glyph** for each control (a paperclip attach vs a
  `+`, camera, mic) and its **left/right order** in the row. These are the cheapest, highest-visibility
  fidelity wins and, across builds, the most commonly dropped - the composer especially.
- **State + population:** every visible state (incoming + outgoing, reactions, attachments, threads,
  typing, receipts, empty). You must be able to reproduce each with a local fixture (Step 6).
- **Viewport + scale:** carried from Step 1.

**Measuring the two sides (the web's edge over native).** The *rendered* side never needs pixel
sampling: `getComputedStyle` returns the exact `color` / `font` / `padding` / `border-radius` - trust
it over any eyeball. Only the *reference* side needs sampling. Sample it with `magick` or Python+PIL
if present; if neither is available, load the reference image into the capture browser (`file://`) and
read pixels with a canvas `getImageData` (the `--sample` mode of the capture script in Step 6). Lo-fi
tier: skip sampling entirely, palette comes from the preset / brand.

### Name the Stream concept behind every signal

For every glyph, badge, pill, and label in the image, name the Stream concept it implies and where it
routes. A signal you cannot name is a region you will silently drop; if it truly matches nothing here,
fetch the product index ([`docs-map.md`](docs-map.md)) before declaring it custom chrome. "Routes to"
cites [`custom-ui.md`](custom-ui.md) contract rows and [`docs-map.md`](docs-map.md) page names - no URLs.

**Chat signals:**

| Visual signal in the image | Stream concept | Routes to |
|---|---|---|
| Single / double tick, "seen" | Read + delivery receipts | contract: message row (receipts); docs Channel Read State |
| Emoji pill with a count | Reactions | contract: message row (reactions); docs Reactions Customization |
| "N replies" under a message | Thread reply summary | contract: message row (thread indicator); docs Thread |
| Mini-quote block above a message | Quoted / replied-to parent | contract: message row (quoted parent); docs Message UI |
| Image grid / file card / audio waveform | Attachments | contract: message row (attachments); docs Voice Recording Attachment |
| Stacked same-author bubbles, one avatar | Message grouping | contract: message row (grouping); docs Message UI |
| "(edited)" / "This message was deleted" | Edited / deleted state | contract: message row (edited/deleted); docs Message UI |
| Floating "Today" / date pill | Date separator | docs Message List |
| Bold row + badge in the sidebar | Unread state | contract: channel preview (unread); docs Channel List UI |
| Dot on an avatar | Online presence | contract: channel preview / header (presence); docs Online Status |
| "X is typing..." | Typing indicator | contract: header (typing); docs Typing Indicator |
| Plus / smiley / mic inside the input | Composer attach / emoji / voice | contract: composer; docs Message Composer UI, Audio Recorder |
| Metadata inside vs below the bubble | Structural message row | contract: message row (injection - `MessageUI`); docs Message UI |
| Hover "..." on a message | Message actions menu | contract: message row (actions); docs Message Actions |
| "No chats yet" / "No messages yet" screen, or a loading skeleton | Empty / loading state | custom `EmptyStateIndicator` / `LoadingIndicator`; docs Channel List UI, MessageList |

**Video signals:**

| Visual signal in the image | Stream concept | Routes to |
|---|---|---|
| Equal grid of tiles | `PaginatedGridLayout` | docs Call layout |
| One large tile + a filmstrip | `SpeakerLayout` | docs Call layout |
| Name label on a tile | Participant label | contract: call layout (each participant); docs ParticipantView |
| Mic-slash on a tile | Mute indicator (`hasAudio`) | contract: call layout (mute indicator); docs ParticipantView |
| Colored ring around a tile | Dominant speaker | contract: call layout (dominant speaker); docs Call layout |
| A desktop / window inside a tile | Screenshare | contract: call layout (screenshare); docs ParticipantView |
| Circular buttons along the bottom | Call controls | contract: call controls; docs Call Control Actions |
| Small self-view thumbnail | Local participant | contract: call layout (each participant); docs ParticipantView |
| Signal / reception bars on a tile | Network quality | docs Network Quality Indicator |
| "LIVE" badge + viewer count | Livestream surface | docs Watching a livestream |

**Feeds signals** (Feeds is headless - every feeds region is bespoke, so the contract always applies):

| Visual signal in the image | Stream concept | Routes to |
|---|---|---|
| Avatar + name + time + text card | Activity card | contract: activity card; docs Feeds, Activities |
| Heart + count | Activity reaction + own-state | contract: activity card (reaction); docs Reactions |
| Speech-bubble + count | Comments | contract: activity card (comments) + comment row; docs Comments |
| Two circular arrows + count | Repost | contract: activity card (repost); docs Activities |
| Bookmark flag | Bookmark | contract: activity card (bookmark); docs Bookmarks |
| "Follow" button | Follow graph | docs Follow and Unfollow |
| "What's on your mind" box | Feed composer | contract: feed composer; docs Activities |
| "X and 2 others..." + a bell | Notification feed | contract: activity card (base) + docs Notification Feeds |
| A tab switcher over the feed | Multiple / For You feeds | docs For You Feed |
| Horizontal bars in a post | Poll activity | docs Polls |

---

## Step 3: Route every region

For each region, name the Stream component, then the cheapest mechanism that reaches the design. The
three axes: **theming** (props + CSS vars, no custom component), **injection** (your own component for
one region -> completion contract), **bespoke** (a headless tree -> completion contract). This table
maps screenshot region -> component + mechanism; [`custom-ui.md`](custom-ui.md)'s table maps a bespoke
region -> its docs page (no duplication).

| Region in the screenshot | Stream component | Cheapest mechanism |
|---|---|---|
| Channel-list rail | `<ChannelList>` + preview | Structural preview -> injection (`ChannelPreviewUI`) -> contract |
| Message row / bubble | `<MessageList>` + row | Almost always structural -> injection (`MessageUI` via `Message=` / `WithComponents`) -> contract |
| Composer / input bar | `<MessageComposer>` | Button placement differs -> injection (`MessageComposerUI`) -> contract |
| Channel header | `<Channel>` header slot | Injection -> contract; or props only (no contract) |
| Participant tile / call layout | `<StreamCall>` + layout | Prebuilt layout, or injection -> contract |
| Call-controls bar | `CallControls` | Prebuilt, or injection (custom controls) -> contract |
| Feed of cards | `useFeedActivities` + your card | Bespoke -> contract (always) |
| Comment list | `useActivityComments` + your row | Bespoke -> contract (always) |
| Post box | `feed.addActivity` + your form | Bespoke -> contract (always) |
| Colors / fonts / spacing only | any | Theming (preset + `str-chat` vars) - no contract |

Rules:
- **Any region where you render your own component fills its [`custom-ui.md`](custom-ui.md) contract**
  (it inherits every sub-feature the prebuilt drew). A theming-only region skips the contract.
- **Injection over headless.** Keep the prebuilt tree; swap only the regions you must.
- **Feeds has no prebuilt UI: every feeds region is bespoke by definition, so the contract always
  applies** - there is no theming-only escape for any feeds region (card, composer, comment row, or
  notification list).

---

## Step 4: Ground the names

Batch-collect every [`docs-map.md`](docs-map.md) row named in Step 3, then `WebFetch` them **in one
pass before building** - confirm the current component / prop / hook names, and confirm they match the
**installed SDK major** (Chat React v14 vs v13 differ). Use the runnable installed-export check in
[`custom-ui.md`](custom-ui.md) (do not restate it here). The capability list is durable; the names come
from the fetch. On fetch failure, hand to the `stream-docs` skill; if neither resolves it, **stop and
ask** ([`../RULES.md`](../RULES.md) > Docs-first). Never build from memory.

---

## Step 5: Build, batched

Implement every region from the spec in one pass:
- **Reuse SDK pieces inside your components** (`<MessageText/>`, `<Attachment/>`, `<Avatar/>`,
  `<ParticipantView/>`) rather than rebuilding them.
- **BEM / class names on a docs page are a structural spec, not shippable CSS** - implement with
  Shadcn + Tailwind.
- **Keep the providers mounted** (`<Chat>` / `<Channel>`, `<StreamVideo>` / `<StreamCall>`,
  `<StreamFeeds>` / `<StreamFeed>`) - injection over headless.

### Palette through the sanctioned channels

Match the reference's colors **without** hand-editing `globals.css` (which [`../RULES.md`](../RULES.md)
> Theme forbids):
- **App chrome** (your shell, buttons, sidebar): the **shadcn preset** closest to the sampled palette
  - do not accept a random preset when a screenshot dictates the colors. *(Track E / existing app: the
  preset is already set; match chrome via the app's existing theme system, and if the chrome must
  change color with no theme lever, surface that to the user. The Stream surface is matched
  regardless.)*
- **Stream chat surface** (bubbles, list, composer): Stream's **`str-chat` theming** - the
  `str-chat__theme-light/dark` class, the SDK's documented CSS custom properties, and `<Channel>`
  theming. **Confirm the current variable names on the Theming page** ([`docs-map.md`](docs-map.md)) -
  do not hard-code variable names from memory.
- **Lo-fi tier:** palette from the preset / brand, never sampled from a pencil sketch.

### The reference frame wins over the generic shell

Apply [`builder-ui.md`](builder-ui.md) > Reference-design override: **drop chrome the reference does
not show** (a bare phone-chat reference has no app top-bar and no channel-list sidebar) and **fill the
viewport** (no fixed-width chat strip beside empty background). The reference is the shell, not a
widget inside the generic shell. The Stream regions themselves must **grow to fill their container** -
the SDK default can cap the channel list at a fixed ~288px and leave the message list / header not
filling; size via the wrapper (flex + `min-w-0`, a height chain) per [`builder-ui.md`](builder-ui.md) >
Layout / sizing.

---

## Step 6: The verify loop

**"Verified" = a screenshot of the rendered app, captured THIS round, compared region-by-region
against the reference, with every spec row measured.** Reading the code, trusting your class names, or
eyeballing the running app (however late or careful) does not count. A match claimed any other way is
not a match; it is a guess that happened to compile.

### 6a. Populate every state - fixtures by default

Every state the reference shows must be **visibly present in the capture**. Default to **local
fixtures** (no backend writes - the no-seeding invariant, [`../../stream/RULES.md`](../../stream/RULES.md)
> No auto-seeding, holds). Enumerate them by product:
- **Chat — content states:** incoming + outgoing, a same-author run (grouping), an attachment, a
  reaction, a quoted reply, long text, a typing event, read receipts, **an empty channel list, an
  empty message list, and (if the design shows one) a loading skeleton**.
- **Chat — interaction / open states (drive them; they do NOT appear at rest):** the hover message
  toolbar (does it shift the bubble?), the **thread panel OPEN** — its own layout, sidebar vs
  full-pane, not just the "N replies" entry point — the reaction selector open, the message-actions
  menu open, the composer with a staged attachment and in edit mode, and the details / right pane
  open. Each has a distinct layout and is a common regression site a resting capture never reaches.
- **Video:** multiple tiles, a muted participant, a screenshare, a dominant speaker.
- **Feeds:** a card with reactions + comments + an image, long text, a notification entry.

**Render fixtures through the standard flow - never a login-bypassing route.** Mount the real
components against your fixtures in a **dev-only view reached AFTER the normal username login and
sitting inside the real AppShell / providers**, so the real layout, providers, and authenticated state
are exercised. **Guard it with an env flag that is code-checked absent in production** (the view
early-returns / 404s when the flag is unset), so a missed cleanup can never ship a live test surface. A
bare route that skips login renders components in a fake context and passes while production differs -
do not use one.

**Reuse the SHIPPED layout - do not hand-roll a wrapper for the fixtures view.** The fixtures view must
render the *same* layout component the app ships (import your real `AppShell` / shell layout and inject
the fixture channel as the active channel); it must **not** re-create its own `<main>` / column
structure. Layout bugs live in the wrapper geometry (flex direction, which node carries `flex-1`,
`min-width:0`, intermediate `str-chat` nodes) - a hand-rolled fixtures wrapper reproduces *different*
geometry and passes while production is broken. The classic trap: a fixtures wrapper that is a flex
**column** (children stretch to full width automatically) hides a width-collapse that only appears in the
shipped flex **row**. If injecting a fixture channel into the real shell is awkward, that awkwardness is
a signal the shell isn't structured for testability - fix the shell, don't fork the layout.

**Opt-in real-data check.** If the user prefers a real-backend pass over fixtures, seed the states into
a **throwaway app provisioned solely for this check and deleted after** - **not** the app the project
connects to (its `.env.local` key), and **not** any app holding other users' data - with explicit
confirmation + tracked teardown, then capture the actual screen. "Dev" is not "disposable": if the only
app available is the project's own, you may **not** seed it; fall back to fixtures. Fixtures stay the
default; when in doubt, use fixtures.

This step is **required**: a claim that a region "would render" / "is wired so it will look right" -
without a this-round capture that actually shows it populated - is not verification, and an unpopulated
fixture is `GAP - not matched`, not an inference.

### 6b. Tool ladder (use the first rung that works; never skip to a lower rung while a higher one works)

A render comes from a browser, not from markup: `curl`-ing the page HTML or reading the served CSS
is **not** a capture (no layout, no computed styles, no fonts resolved). Use the first rung that works
and do not substitute a static read for it.

1. **In-session browser tooling, if present.** Anything that loads a URL at a set viewport,
   screenshots it, and reads computed styles / the DOM. Examples: a Preview MCP
   (`preview_start` / `preview_screenshot` / `preview_inspect` / `preview_resize`) or a connected
   Chrome - *examples of a capability*, use whatever the session exposes. Before concluding it is
   absent, **state which capture tools you checked for**; an unstated "no tooling here" is not a reason
   to descend.
2. **Playwright fallback - mandatory whenever `node` / `npm` are available.** Announce first (published
   by Microsoft, `microsoft/playwright`; ~120MB of Chromium to the shared Playwright cache), then
   **actually run** it - installed into a **self-contained `.design-verify/` harness with its own
   `package.json`, so the app's `package.json` / lockfile are never touched** (Track E may be a
   yarn / pnpm project - **never add playwright to the app root with any manager** - no `npm install`, `pnpm add`, or `yarn add` there; the harness install below is npm-only whatever the app uses):
   ```bash
   mkdir -p .design-verify && printf '{"private":true}\n' > .design-verify/package.json
   npm install --prefix .design-verify -D playwright
   .design-verify/node_modules/.bin/playwright install chromium   # add --with-deps on Linux CI
   ```
   Descend to rung 3 **only if that command actually errors** - paste the failure. Predicting "this
   looks sandboxed / offline, it would fail" and skipping the install is **not** permitted; run it and
   observe. Never fake a capture and never claim rung 2 ran when it did not. *(If the project has **no runnable app at all** - nothing to serve -
   that is a prerequisite failure: report UNVERIFIED per 6e and do not install a browser to screenshot
   nothing. Not having **built the fixtures view yet** is not this case - build it, then capture; in a
   design-matching task the app exists by definition, so this rarely applies.)*
3. **Last resort - manual with the user.** Only after rung 1 was checked and rung 2 was *run and
   errored* (show both). Give the user the dev-server URL, the viewport, and the spec table, and ask
   them to compare. Until the user confirms, **every region is implemented but UNVERIFIED** - say
   exactly that, and never imply a match you did not see.

### 6c. Capture recipe

1. Start the dev server in the background (SKILL.md port convention: a random 5-digit port).
2. Log in through the standard Login Screen and open the env-guarded fixtures view (or, on the opt-in
   real-data path, navigate to the seeded screen).
3. Set the **Step 1 viewport** and `deviceScaleFactor: 2`.
4. **Do not wait for `networkidle`** - Stream holds a WebSocket open for the whole session, so the
   network never goes idle and a `networkidle` wait blocks until timeout. Wait for `domcontentloaded`,
   then wait for a rendered Stream selector to actually appear (e.g. `.str-chat__message-list`
   containing at least one message row / `.str-chat__li`), then ~500ms for images / animations to settle.
5. Produce, per screen: **(a)** a full-screen screenshot; **(b)** **element crops** of the high-detail
   regions (the composer, one message row, one tile / card) - detail is lost in a full-page shot;
   **(c)** a **probe pass** that, for each selector in your probe list, returns its
   `getBoundingClientRect` + the `getComputedStyle` values you need and a `missing: true` flag when the
   selector matches nothing (that flag IS the structural-presence check in 6d); **(d)** optionally,
   sample the reference image for the color rows (`magick` / PIL, or a canvas `getImageData` over a
   `file://` load).
6. **Then drive and re-capture the interaction / open states (6a).** They don't render at rest, so
   after the resting capture: `hover()` a message row and assert its bubble `getBoundingClientRect`
   is unchanged (a shift means an in-flow hover toolbar — move it out of flow); `click()` a "N
   replies" button to open the thread and capture the open panel (sidebar vs full-pane is decided
   here); open the reaction selector, actions menu, and details pane the same way. Each opened state
   is its own screenshot + probe. A capture with zero driven states is incomplete.

**Two capture gotchas that waste a round if missed:**
- **Capture with a real Chromium build, not the OS headless binary.** A bare system `chrome --headless`
  frequently screenshots only the app splash / loading state; use Playwright's bundled Chromium (rung 2
  installs it) or launch with `--channel=chrome`.
- **Disable the Next.js dev indicator first** (`devIndicators: false` in `next.config`, or dismiss the
  overlay). It parks in a screen corner and can occlude the composer or a bottom message row in the shot.

With in-session tooling, use its screenshot + computed-style calls directly. With the Playwright
harness, write your own small runner **in `.design-verify/`** (its own `package.json` means CommonJS
`require` and ESM both work; use a `.cjs` extension to force CommonJS if you prefer) - the
`npx playwright screenshot` CLI cannot run probes, so a script is needed. **Write it AND run it**
(`node .design-verify/<runner>`); the probe's actual stdout is the artifact you cite in 6d - a runner
authored but not executed produces no Rendered values. Probe shape:

```
// probe list: [{ selector: '.str-chat__message-text', props: ['color','font-size','font-weight'] }, ...]
// each probe -> { selector, rect, styles: { ... } }   OR   { selector, missing: true }
```

### 6d. Compare protocol (four checks per round, in order)

1. **Read both images side by side.** Numbers can pass while the screen reads wrong (font fallback,
   seams, weight). Name the specific things you checked (seams, font shape, weight, alignment, overall
   balance) - a bare "reads the same" with nothing named is not a completed check. **Loop until the
   side-by-side reads as the same screen, not just until the numbers match.**
2. **Computed-style diff**, mapping each spec field explicitly:
   - color -> `color` / `background-color`
   - type -> `font-family` / `font-size` / `font-weight` / `line-height`
   - dimensions -> the rect + `border-radius` / `padding` / `gap`

   Tolerances: dimensions within `+/-2` CSS px; colors within a small band of the sampled value (about
   `+/-3` per 8-bit channel, to absorb anti-aliasing - a visible hue / shade change is a FAIL), stating
   both hex values on every color row; **`font-family` must resolve to the intended family - a fallback
   to serif/sans is a FAIL, not a rounding error.**
3. **Region-fills-container check (mandatory).** For every Stream region, probe its
   `getBoundingClientRect().width`/`height` against its parent's, and the main message list against the
   available viewport (viewport minus any sidebar). A region collapsed to a narrow/default size when it
   should fill - the message list stuck at a "mobile" width, a channel list at the ~288px default - is a
   FAIL, even when every color/type/radius value passes. This is the check that catches a sizing bug the
   eyeball misses when the content happens to be short; it is not optional. **Vertical counts too:** the message list must fill its pane height and
   **bottom-anchor** short content (a conversation pins to the composer; it must not float at the top with
   a blank band below), and any wallpaper / background must cover the **full pane height** - a background
   that stops where the messages stop is a FAIL even when every width passes. Example probe: emit
   `{ selector, rect, parentWidth, parentHeight }` for `.str-chat__channel`, `.str-chat__main-panel(-inner)`,
   the message list, and the background element, and assert both `width >= parentWidth - scrollbar` and
   `height >= parentHeight - scrollbar`.
4. **Structural presence** via the probe `missing` flags: every Step 2 taxonomy signal must exist in
   the DOM. A `missing:true` is a dropped region.

Output a per-region discrepancy table. Every "Rendered" value is copied from this round's probe output
/ capture, and the Source cell names the file - a row with no Source is UNVERIFIED, not PASS:

| Region | Spec | Rendered (this round) | Source (capture file + probe) | Verdict | Fix |
|---|---|---|---|---|---|
| ... | ... | ... | ... | PASS / FAIL | ... |

**Completeness gate.** Every signal named in Step 2's taxonomy and every row of the applicable
[`custom-ui.md`](custom-ui.md) contract must have a probe selector and a table row. Before exit, diff
the probe list against the taxonomy - any taxonomy entry with no probe is an unverified region (treat
as FAIL), never a silent omission. Each high-detail region (composer, one message row, one tile / card)
must also have an element crop cited in its Source cell - a full-page shot alone does not satisfy a
high-detail row. A short table is an incomplete spec, not an early finish.

### 6e. Iterate and exit honestly

Fix **all** failing rows, **then** recapture **once** (work in batches - not one recapture per row).
**Loop cap: 5 rounds.**

Exit only when every spec row is **PASS with this-round evidence**: the final claim cites the last
capture. "This round" = the capture taken after your most recent edit to any file affecting the
previewed regions (components, CSS / theme, fixtures, preset). *Any* such edit - however small -
invalidates the prior capture; if `git status` shows changes to those paths since the cited capture, it
is stale and you re-capture before claiming PASS.

**If no capture happened this round on any rung** (tooling absent, install failed, app unreachable),
the deliverable says **UNVERIFIED** and lists which regions are implemented-but-unseen. Do not describe
any region as "matched" or "verified" in the delivery when you never rendered it - a note-to-self that
it is unverified does not license a customer-facing "it matches." UNVERIFIED still requires the fixtures
view to be **built** and its states populated - "unseen" means the capture tooling failed, not that you
skipped the fixtures work; an UNVERIFIED deliverable with no fixtures view built is an unfinished task,
not an honest exit.

At the cap, report each unresolved row as **`GAP - not matched`** (the [`custom-ui.md`](custom-ui.md)
vocabulary), with **both measured values** (spec vs rendered) and the honest reason. "Deferred",
"minor", "close enough", and "cosmetic" are banned relabels of a GAP.

**"Genuine impossibility"** (the only pre-cap reason to skip a region) means the SDK or platform cannot
express it at all - cite the specific limitation, not "hard to fixture", "fiddly", or "low on time". A
region you skip for *any* reason is still a row in the discrepancy table marked `GAP - not matched` with
the reason (impossible regions included), never a prose footnote. Time pressure is never impossibility.

**Cleanup at exit (finally-style - run it even on failure or interruption):** delete the entire
`.design-verify/` harness (its `package.json` / `node_modules` included - nothing landed in the app
manifest, so there is no app devDependency to disclose); remove the dev-only fixtures view + its env
flag and confirm it is gone (it is also code-guarded out of production, so a missed cleanup cannot ship
a live surface). If you used the opt-in disposable-app seed, tear down every seeded resource and verify
the deletion.

### 6f. Anti-rationalization

Matching a design under time pressure breeds excuses. The discrepancy table decides, not adjectives.

| Excuse | Reality |
|---|---|
| "It's close enough / basically there" | The table decides with measured values, not an adjective. |
| "I verified it by reading the code" | Code is not a render. Capture this round or it is UNVERIFIED. |
| "There's no browser tooling here" | The ladder has three rungs. Rung 2 (Playwright) installs; rung 3 is labeled UNVERIFIED. |
| "Screenshots are too slow to loop" | The loop is batched: decompose/build all, ~5 captures total, not one per tweak. |
| "The computed styles all match" | The side-by-side Read is mandatory every round - numbers miss font fallback, seams, weight. |
| "Colors/type all match, so the region's fine" | Run the region-fills-container check (6d.3). A region collapsed to a mobile/default width passes every color/type row and is still a FAIL. |
| "I built a quick wrapper for the fixtures view" | Verify in the SHIPPED layout component, not a hand-rolled wrapper. A flex-column stand-in hides a width-collapse that only appears in the shipped flex-row - you verified a different screen than you ship. |
| "I rendered every state in the fixtures" | Rendering isn't driving. Hover/open states (thread panel, hover toolbar, reaction picker, actions menu) only exist after you `hover()`/`click()` - a resting capture misses them (6a/6c). |
| "`next build` passed" | Compiling is not matching. A green build says nothing about the pixels. |
| "The user can just check it" | That is rung 3 only, and only after rungs 1-2 fail - and it ships labeled UNVERIFIED. |
| "I'll curl the HTML / read the served CSS instead" | Static markup is not a render - no layout, no computed styles, no resolved fonts. Use a browser rung (1 or 2). |
| "The font won't install, so I'll note it as minor" | An unresolved row is `GAP - not matched` with both measured values, never "minor". |
| "I'll `pnpm add` / `yarn add` playwright instead" | Any add in the app root corrupts its lockfile. Install only into the `.design-verify/` harness (`npm install --prefix`), whatever the app uses. |
| "I wrote the probe / capture script" | Writing it is not running it. Run it this round; its real stdout is the evidence - an authored-but-unrun script proves nothing. |

**Red flags - stop:**
- Claiming "matches" without a capture taken **this round**.
- Ending with failing rows left unlabeled, or a GAP relabeled "deferred" / "minor" / "cosmetic".
- Skipping the composer or the receipts rows because they are fiddly.
- Downgrading a measured FAIL to a soft word to close the task.
