# Stream React (web) - matching a reference design (screenshot / Figma / "make it look like X")

Run this whenever the request carries a **target appearance** - an attached screenshot, a Figma
frame, or "make it look like WhatsApp / Slack / Linear / <app>". A reference design is a **checklist
of regions**, not a color tweak: the rail width, the message-row layout, where the timestamp and
receipts sit, the composer's button placement, the header - most differ from Stream's defaults
*structurally*, not just by color. Stopping at "wallpaper + bubble color" is the known failure mode.

This file is the *procedure*. The *decision* (customize prebuilt vs go bespoke) and the per-region
**completion contract** live in [`custom-ui.md`](custom-ui.md); every region's current props/hooks
come from the live page in [`docs-map.md`](docs-map.md). Still **prebuilt-component-first** and
**docs-first** ([`../RULES.md`](../RULES.md) > Reference authority, Docs-first) - matching a design
never licenses building from memory.

## Work in batches - decompose all, build all, verify once

A full match is many regions; do **not** build-and-screenshot after every tweak. Decompose every
region into a written spec first, ground the names once, implement all regions in one pass, then run
the app once and verify region-by-region. Iterate on the whole surface, not one control at a time.

## Step 1: Decompose the reference into a written spec (before any code)

**Read the image.** Then write the spec down - do not hold it in your head, and do not start coding
from an impression:

- **Regions / layout:** the columns and bars - conversation-list rail (and its width), main message
  list, composer, header, thread panel, any secondary rail or pinned banner. Name every region you
  can see; a region you don't name is a region you'll silently drop.
- **Component inventory:** per region, the sub-elements present - avatar, author, timestamp,
  reactions, reply/thread summary, receipts, attachment tiles, composer buttons. This inventory is
  what the completion contract holds you to.
- **Color - sample, don't guess:** sample the actual hex of each sub-part (app chrome, list
  background, incoming vs outgoing bubble, text, muted text, accent, unread badge, online dot). A
  "weird line" between two regions is usually a **color seam** (two backgrounds meeting), not a
  divider element. A background may be a **texture / gradient / image**, not a flat color.
- **Type:** family, weight, size, line-height per text role (author, body, timestamp, unread).
  **Weight is its own axis** - match it separately from size.
- **Dimensions - measure, don't eyeball:** rail width, avatar size, bubble radius + padding, row
  gap, header height. Read pixels off the image; do not invent round numbers (16 / 24 / 32).
- **State + population:** is the screenshot populated (messages, reactions, attachments, threads,
  typing) or empty? Note every visible state - you must reproduce it to verify (Step 6).

## Step 2: Route each region to a component + mechanism

Map every region to its Stream component, then to the cheapest mechanism that reaches the design.
**Three axes** (from [`custom-ui.md`](custom-ui.md) Step 0):

| Region in the screenshot | Stream component | Typical mechanism |
|---|---|---|
| Conversation-list rail | `<ChannelList>` + channel preview | Preview differs structurally -> **injection** (`ChannelPreviewUI`) -> completion contract |
| Message row / bubble | `<MessageList>` + message row | Almost always structural -> **injection** (`MessageUI` via `Message={...}` / `WithComponents`) -> completion contract |
| Composer / input bar | `<MessageComposer>` | Button placement differs -> **injection** (`MessageComposerUI`) -> completion contract |
| Top bar / channel header | `<Channel>` header slot | Injection (custom header) or props |
| Colors / fonts / spacing only | any | **Theming** (shadcn preset + `str-chat` CSS variables) - no contract |
| Call layout / participant tile / controls | `<StreamCall>` + layout | Injection -> completion contract (Video rows) |

**Rule:** any region where you render your **own** component inherits every sub-feature the prebuilt
rendered - fill that region's row in the [`custom-ui.md`](custom-ui.md) completion contract
(attachments, reactions, quoted replies, receipts, threads, ...). A region matched by **theming
only** (props + CSS vars, no custom component) skips the contract. Prefer **injection** (keep the
prebuilt tree, swap the regions you must) over a fully-headless rebuild.

## Step 3: Match the palette through the sanctioned channels (not hand-CSS)

You can match a screenshot's colors **without** hand-editing `globals.css` (which
[`../RULES.md`](../RULES.md) > Theme forbids):

- **App chrome** (your shell, buttons, sidebar): the **shadcn preset** - pick or generate the
  `--preset` closest to the sampled palette in Step 1b; don't accept a random preset when a
  screenshot dictates the colors. *(Track E / existing app: the preset is already set - match chrome
  via the app's existing theme system; if the chrome itself must change color and there is no theme
  lever, surface that to the user. The Stream chat surface below is matched regardless.)*
- **Stream chat surface** (bubbles, list, composer): Stream's **`str-chat` theming** - the
  `str-chat__theme-light/dark` class plus the SDK's CSS custom properties, and `<Channel>` theming.
  **Confirm the current variable names** on the Theming page ([`docs-map.md`](docs-map.md) Chat
  cookbook -> theming) - do not hard-code variable names from memory.

This is the design-matching carve-out to "don't touch `globals.css`": theme via presets + documented
Stream variables, not ad-hoc CSS overrides.

## Step 4: Ground the names (don't guess)

Before writing markup, `WebFetch` each region's live page from [`docs-map.md`](docs-map.md) to
confirm the current component / prop / hook names, and confirm they match the **installed SDK major**
(Chat React v14 vs v13 differ - see [`enhance.md`](enhance.md) E1, or the scaffold's resolved
version). The capability list is durable; the names come from the fetch.

## Step 5: Build (batched)

Implement every region from the spec in one pass, **reusing** SDK pieces inside your components
(`<MessageText/>`, `<Attachment/>`, `<Avatar/>`, `<ParticipantView/>`) rather than rebuilding them.
Any BEM / class names on a docs page are a **structural spec, not shippable CSS** - implement with
Shadcn + Tailwind. Keep the providers mounted (injection over headless).

## Step 6: Verify against the reference (mandatory - render and compare)

A match is not done until you run it and compare, region by region, against the target:

1. **Seed the states the screenshot shows.** If it shows a populated conversation, create a
   **throwaway** seed (messages incoming + outgoing, a same-author run for grouping, an attachment,
   a reaction, a reply/thread, long text, a typing event) so every region is visible. This is a
   **verification-only** carve-out to the no-auto-seeding rule
   ([`../stream/RULES.md`](../stream/RULES.md)): seed to verify, then **delete it before delivery** -
   never ship demo data the user did not ask for.
2. **Render and inspect.** If browser-preview tooling is available (e.g. the Preview MCP:
   `preview_start` / `preview_screenshot` / `preview_inspect` / `preview_resize`), start the dev
   server, screenshot the real screen on its actual navigation path, and **inspect computed `color`
   / `font` / `padding` / `border-radius`** against the sampled spec from Step 1; `preview_resize`
   to the breakpoints the screenshot implies. Computed-style inspection is exact - trust it over
   eyeballing. If no preview tooling is present, run the dev server and compare in a browser
   manually.
3. **Compare region-by-region and iterate.** Fix drift until each region matches. **Implement every
   region, the composer included** - a region left at the SDK default is a FAIL, not a "known
   cosmetic gap".
