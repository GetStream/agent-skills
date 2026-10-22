# Stream Agents in React

Run this when the app talks to a Stream Agent: an `agents/<name>/` folder synced with
`getstream agents`, and sessions opened with `@stream-io/calypso`. The agent - its models,
guardrail, knowledge and routing - runs on Stream. The app opens sessions, renders them
with the Chat and Video UI kits, and runs any tools it registers.

## Docs

```bash
d=$(getstream docs agents/javascript)
cat $d/INDEX.md                      # quickstart: agent folder, tools, chat UI
cat $d/sessions.md                   # sessions, voice, events, history
cat $d/auth.md                       # user tokens
cat $d/tool-calling-and-dispatch.md  # browser tools vs a Dispatch worker
cat $d/creating-an-agent.md          # agent.yaml keys
```

When the docs and the SDK disagree, the SDK's types win (`node_modules/@stream-io/calypso/dist/*.d.ts`).
The backend source is github.com/GetStream/Vision-Agents.

## Setup

- The `getstream agents` commands need the beta CLI (see stream skill). Run
  `getstream init`, then `getstream agents init <name> --template voice` (or `text`). It
  also creates the `agent` call type and channel type that sessions need. Edit the
  folder, then `getstream agents sync <name>` and `getstream agents test <name>`.
- Install `@stream-io/calypso` with the UI kits: `stream-chat stream-chat-react` for the
  conversation, `@stream-io/video-react-sdk` for voice. Calypso marks them optional peers;
  this runbook uses them.
- Token route as in SKILL.md. One user token signs in Calypso, Chat, and Video. The
  browser `Client` gets the `apiKey` and `setUser`, never the secret.

## Client

- Create one Calypso `Client` at the app shell, next to the Chat and Video clients, and
  hand those over with `client.use({ chat, video })`. Without it, `session.chat()` and
  `session.video()` open second connections as the same user.
- `import "@stream-io/calypso/chat"` and `"@stream-io/calypso/video"` once, from a
  `'use client'` module. Without them `session.chat()` / `session.video()` throw.
- **Transcript:** the session's channel is the transcript, for text and for voice. Get
  it with `const { channel } = await session.chat()` and render it with `<Chat>`,
  `<Channel>`, `<MessageList>` and `<AIStateIndicator />`. On voice, the backend writes
  each spoken turn there (custom `source: "speech"`), streams the agent's reply into a
  message (`generating: true` while it streams), and marks a reply the caller cut off
  `interrupted: true` - usually with its text cleared. Speech the agent ignored is
  deleted. Don't build a second transcript list from `session.events()`.
- **AI replies:** pass `isMessageAIGenerated={(m) => Boolean(m.ai_generated)}` to
  `<Chat>` and keep the AI defaults from SKILL.md. If agent replies render as plain
  messages, the check below shows `ai_generated: null`: the backend isn't marking them -
  report it, don't patch the predicate. In a custom `Message`, skip messages with no
  text and no attachments (the default renders an empty bubble) and mark `interrupted`
  ones as cut off. Type the custom fields once instead of
  casting, in a `stream-chat.d.ts` that starts with `import "stream-chat";` (without it
  the file replaces the module instead of extending it):
  `declare module "stream-chat" { interface CustomMessageData { ai_generated?: boolean;
  source?: "speech" | "agent"; generating?: boolean; interrupted?: boolean } }`.
- **Composer:** the agent doesn't answer messages posted to the channel, so the
  composer sends with `overrideSubmitHandler` calling `session.responses.create(text)`.
  That sends only the text, so hide the attachment button (`WithComponents` override
  `AttachmentSelector` with a component that renders nothing). Hide or disable it while voice is on: a typed turn in a voice session is not marked
  finished, so the next `responses.create` is refused.
- **Stop:** while `AIStateIndicator` shows a state, `MessageComposer` swaps Send for a
  Stop button whose default sends `ai_indicator.stop`, which the agent ignores. Replace
  it with `<WithComponents overrides={{ StopAIGenerationButton }}>` and a button of your
  own whose `onClick` calls `session.interrupt()` (the default isn't exported).
- **Voice:** create the session with `start_voice: true`. `session.video()` throws until
  voice is on. Join its call with the Video React SDK (`<StreamCall>`, and
  `<ParticipantsAudio>` to play the agent - check its props in video/react) instead of
  binding `<audio>` elements by hand.
- **Status:** `session.events()` drives status UI, not the transcript. Map `event.kind`:
  `hearing` / `heard` (listening), `responding` (thinking), `interrupted` and `turn`
  (back to listening; `turn` also carries timings), and `left` (the agent left - show
  the call as ended). Take "speaking" from the agent participant's `isSpeaking` in
  `useRemoteParticipants()`: `spoke` fires when a piece finishes synthesizing, not
  when its audio plays, and `responded` means the model finished, not the speech.
- Create the session and join the call from a user action (a Start button), not at
  module scope: module code runs during SSR and again on every hot reload. A session has one event stream - two
  loops take half the events each - so read it in one place and fan out.
- A copilot that listens to a call between people, rather than talking in it, shows the
  call's closed captions from the Video SDK (video/react), not a chat list.
- **Ending:** `session.close()` ends the conversation and keeps its history; with voice
  on, the agent leaves the call. Call it from the hang-up control and when the user
  leaves the page.

## Pitfalls

- The greeting is spoken the moment the agent joins, whoever is listening. Set
  `greeting: { text: "" }` in agent.yaml and `session.say()` it once the user has joined
  the call.
- Lines spoken with `session.say()`, the greeting included, reach the channel only on
  backends that record them; on older ones they are heard but missing from the
  transcript. The router's idle check-ins ("are you still there?") are written from a
  different user than the agent's replies. Run the check below on a real call before
  relying on the channel. For a complete record after the call, read
  `session.responses.items.all()` (`said`, `answer`).
- Tool calls don't appear in the channel, with or without `displayTitle`. UI that reacts
  to a tool - a form filling in, a confirmation - comes from the tool's own `run`.
- Tools passed to `sessions.create({ tools })` from the browser run in the page, over the
  session socket, with no worker. Tools on `agent.tools` only run where a `Dispatch`
  worker hosts them.
- On a voice agent, every custom tool result triggers another model call before the
  agent speaks, which can add seconds per turn. Measure first (`turn` events). Only if
  that latency is too slow, keep the voice agent tool-free and let a text-mode session of
  a second agent, fed each exchange, call the tools.
- A session takes one response at a time: `responses.create` while one runs fails with
  "a response is already running". Queue and retry.
- Don't test a voice session by typing into it with `responses.create`. The typed turn
  is not marked finished, so the next `responses.create` is refused. Use `session.say()` for the agent's
  side and a real microphone, or `getstream agents simulate`, for the user's.
- Pick model routes by measuring them. The `turn` event's `speech_end_to_audio_ms` is
  voice in to voice out; route names that sound fast aren't always the fastest.

## Check the channel

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"agent:<session-id>"},"message_limit":20}' \
  --jq '.channels[0].messages[] | {user: .user.id, text: (.text // "" | .[0:40])} + ([ "ai_generated", "source", "generating", "interrupted" ] as $k | . as $m | reduce $k[] as $f ({}; .[$f] = (if ($m | has($f)) then $m[$f] else $m.custom[$f] end)))'
```

The channel id is the session id under the `agent` type. Each line shows the custom
fields the UI depends on; `null` means the backend didn't set it.

## Verify

- Text: a message sent from the composer gets a streamed, markdown-rendered reply in `MessageList`.
- Voice: the agent is heard after the user joins, both sides' turns appear in `MessageList` as they are said, the agent's replies render as AI messages, and `turn` events report timings.
- No component renders transcript lines from `session.events()`.
- Stop, pressed while a reply streams, ends that reply (`session.interrupt()`).
- The composer is hidden or disabled while voice is on.
- Hanging up calls `session.close()`, and the agent leaves the call.
- The channel check matches what the UI shows as the transcript.
- `getstream agents simulate <name>` passes, and `tsc --noEmit` passes.
