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
- **Text:** `session.chat()` returns the session's channel. Render it with `<Chat>`,
  `<Channel>` and `<MessageList>`. The agent doesn't answer messages posted to the
  channel, so the composer sends with `overrideSubmitHandler` calling
  `session.responses.create(text)`. Agent replies carry `ai_generated`: pass
  `isMessageAIGenerated` and keep the AI defaults from SKILL.md.
- **Voice:** create the session with `start_voice: true`. `session.video()` throws until
  voice is on. Join its call with the Video React SDK (`<StreamCall>`, and
  `<ParticipantsAudio>` to play the agent - check its props in video/react) instead of
  binding `<audio>` elements by hand.
- Live captions and timings come from `session.events()`: `hearing`, `heard`,
  `response_delta`, `responded`, `turn`. A session has one event stream - two loops take
  half the events each - so read it in one place and fan out.
- **Ending:** `session.close()` ends the conversation and keeps its history; with voice
  on, the agent leaves the call. Call it from the hang-up control and when the user
  leaves the page.

## Pitfalls

- The greeting is spoken the moment the agent joins, whoever is listening. Set
  `greeting: { text: "" }` in agent.yaml and `session.say()` it once the user has joined
  the call.
- A voice session's channel is not a full transcript. Model replies and typed turns are
  written to it; `say` lines (the greeting) are not; the router's idle check-ins ("are you
  still there?") are, but from a different user than the agent's replies. Before relying
  on the channel for spoken turns, run the check below on a real call. For a complete
  record after the call, read `session.responses.items.all()` (`said`, `answer`).
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
  is not marked finished, so the next one is refused. Use `session.say()` for the agent's
  side and a real microphone, or `getstream agents simulate`, for the user's.
- Pick model routes by measuring them. The `turn` event's `speech_end_to_audio_ms` is
  voice in to voice out; route names that sound fast aren't always the fastest.

## Check the channel

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"agent:<session-id>"},"message_limit":20}' \
  --jq '.channels[0].messages[] | {user: .user.id, text: (.text // "" | .[0:60]), attachments: [.attachments[]?.type]}'
```

The channel id is the session id under the `agent` type.

## Verify

- Text: a message sent from the composer gets a streamed, markdown-rendered reply in `MessageList`.
- Voice: the agent is heard after the user joins, captions follow both sides, and `turn` events report timings.
- Hanging up calls `session.close()`, and the agent leaves the call.
- The channel check matches what the UI shows as the transcript.
- `getstream agents simulate <name>` passes, and `tsc --noEmit` passes.
