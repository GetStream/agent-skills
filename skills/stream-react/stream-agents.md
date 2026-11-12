# Stream Agents in React

Run this when the app talks to a Stream Agent: an `agents/<name>/` folder synced with
`getstream agents`, and sessions opened with `@stream-io/stream-agents`. The agent - its models,
guardrail, knowledge and routing - runs on Stream. The app opens sessions, shows them with the
Chat SDK's AI components (`stream-chat-react/ai-components`), joins voice calls with the Video
React SDK, and runs any tools it registers.

## Docs

```bash
d=$(getstream docs agents)           # one doc set; each page has every SDK's code
cat $d/quickstart.md                 # agent folder, tools, chat UI, voice UI
cat $d/sessions.md                   # sessions, voice, events, history
cat $d/responses-create.md           # asking: text, images, reasoning effort, UI actions
cat $d/auth.md                       # user tokens
cat $d/tool-calling-and-dispatch.md  # browser tools vs a Dispatch worker, approvals
cat $d/generative-ui.md              # replies with UI: A2UI, OpenUI
cat $d/creating-an-agent.md          # agent.yaml keys

c=$(getstream docs chat-sdk/react/v15)
cat $c/ai-components.md                          # Quickstart: install, styles, wiring, voice
cat $c/ai-components/conversation-view.md        # AIConversation
cat $c/ai-components/reasoning-and-tool-calls.md # steps, tool approvals
cat $c/ai-components/composer.md                 # AIMessageComposer
cat $c/ai-components/voice-visualizations.md     # VoiceGlow, VoiceWave
cat $c/ai-components/use-cases/voice-agent.md    # a voice agent end to end
cat $c/ui-cookbooks/ai/voice-agent-visuals.md    # the voice agent's look
```

When the docs and the SDKs disagree, the types win
(`node_modules/@stream-io/stream-agents/dist/*.d.ts`, and `stream-chat-react`'s for the
components). The backend source is github.com/GetStream/Vision-Agents.

## Setup

- The UI below needs `AIConversationController` from `stream-chat-react/ai-components`:
  stream-chat-react 15.0.1 or later, or 14.17.0 or later on v14. A new app installs the
  latest. In an existing app, pin the installed major (chat-versions.md) and check
  `grep -rl AIConversationController node_modules/stream-chat-react/dist/types`. If it's
  missing, ask the user before upgrading: a newer release of the same major first; from an
  older major, one major per pass, as SKILL.md's "Upgrading an SDK version" says. If they
  decline, tell them this runbook's Stream Agents UI needs those versions, and stop - don't
  hand-roll it.
- The `getstream agents` commands need the beta CLI (see stream skill). `getstream agents
  init <name> --template voice` (or `text`) creates the folder and also the app-wide `agent`
  call type and channel type that sessions need. Ask the user before running it: run
  `getstream status` first and tell them which app it will change. Then edit the folder,
  `getstream agents sync <name>` and `getstream agents test <name>`.
- Install `@stream-io/stream-agents stream-chat stream-chat-react @stream-io/video-react-sdk`.
  `@stream-io/stream-agents/video` brings in `@stream-io/video-client` with the Video React SDK:
  don't install it separately.
- Load the SDK's stylesheet and then the AI components' one, once, where the app starts
  (`$c/ai-components.md`, "Step 2: Install the SDKs").
- Token route as in SKILL.md. Create one Stream Agents `Client` and call `setUser` when the
  user signs in; it never gets the secret. One user
  token signs in Stream Agents, Chat, and Video. If the app already has its own `StreamChat` or
  `StreamVideoClient`, hand them over with `api.use({ chat, video })`, or sessions open second
  connections as the same user.
- The components and the SDK use browser APIs: put them in `'use client'` modules.

## Conversation and view

Build it as the agents quickstart's "Add the chat UI" step shows (`$d/quickstart.md`), with
`$c/ai-components/conversation-view.md` for the view. Rules the docs leave to you:

- One `AgentChat` and one `AIConversationController` per session id, made in an effect keyed
  on it, so React Strict Mode's remount makes fresh ones. The cleanup disposes the controller
  and closes the chat.
- Tools the browser registers go to both `sessions.create` and `sessions.resume`, or a
  resumed conversation can't run them.
- Never post to the channel - the agent doesn't answer it. Asking goes through the session,
  which the controller does when the composer sends. Don't build a second transcript from
  `session.events()`.
- `chat.close()` deletes a new conversation nothing was asked in, so an unused one doesn't
  show in the list; any other is ended and keeps its history.
- Reasoning, tool calls and generative UI are steps and fields of the reply that
  `AIConversation` renders: don't render them yourself. For generative UI, read
  `$d/generative-ui.md` and ai-integration.md's "Generative UI" section.

## Tool approvals

For tools that ask before they run, give the controller an approver that answers through
the chat's session, as `$c/ai-components/reasoning-and-tool-calls.md` ("Tool approvals")
shows. Validate what a tool's `run` receives - the arguments are model output.

## Voice

Build it as the agents quickstart's "Add the voice UI" step shows, with
`$c/ai-components/use-cases/voice-agent.md` for a full voice agent and
`$c/ui-cookbooks/ai/voice-agent-visuals.md` for its look. Rules the docs leave to you:

- Start voice from a click: a browser asks for the microphone and plays audio only after one.
- Keep the composer hidden while voice is on: a typed turn in a voice session is not marked
  finished, so the next one is refused.
- What the agent is doing comes from the voice session's snapshot (`voice.get()`, its
  `status`), not from `session.events()` or participants.
- Show the snapshot's `failure` (a denied microphone, a failed join).
- The transcript is the same `AIConversation`. Replies are written ahead of the voice; the
  voice agent use case's "Reveal replies as they're spoken" paces them for its own
  transcript. On `AIConversation` that would go in an `AssistantMessage` override - check the
  types before promising it, and say so in the summary if it isn't done.
- A copilot that listens to a call between people, rather than talking in it, shows the
  call's closed captions from the Video SDK (video/react), not a conversation.

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
- Tools passed to `sessions.create({ tools })` from the browser run in the page, over the
  session socket, with no worker. Tools on `agent.tools` only run where a `Dispatch`
  worker hosts them.
- On a voice agent, every custom tool result triggers another model call before the
  agent speaks, which can add seconds per turn. Measure first (`turn` events). Only if
  that latency is too slow, keep the voice agent tool-free and let a text-mode session of
  a second agent, fed each exchange, call the tools.
- A session takes one response at a time: `responses.create` while one runs fails with
  "a response is already running". Queue and retry.
- Don't test a voice session by typing into it with `responses.create`: the typed turn is
  not marked finished, so the next `responses.create` is refused. Use `session.say()` for the agent's side and a real
  microphone, or `getstream agents simulate`, for the user's.
- Pick model routes by measuring them. The `turn` event's `speech_end_to_audio_ms` is
  voice in to voice out; route names that sound fast aren't always the fastest.

## Check the channel

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"agent:<session-id>"},"message_limit":20}' \
  --jq '.channels[0].messages[] | {user: .user.id, text: (.text // "" | .[0:40]), steps: [.attachments[]?.type]} + ([ "ai_generated", "source", "generating", "interrupted" ] as $k | . as $m | reduce $k[] as $f ({}; .[$f] = (if ($m | has($f)) then $m[$f] else $m.custom[$f] end)))'
```

The channel id is the session id under the `agent` type. Each line shows the custom
fields the UI depends on, and the reply's steps (`ai_reasoning`, `ai_tool_call`); `null`
means the backend didn't set it. `fromStreamMessage` treats a message as the agent's only
when `ai_generated` is true - a reply without it shows as the user's: report it, don't patch
the adapter.

## Verify

- Text: a question sent from the composer appears at once, the agent shows as thinking, and
  the reply streams in `AIConversation` with markdown, its reasoning and its tool calls.
- Stop, pressed while a reply streams, ends it and keeps what was written.
- A tool that asks first shows an approval card; Allow runs it and Decline doesn't.
- Leaving a new conversation without asking anything leaves no session behind
  (`chat.close()`); reopening one by id shows its history.
- Voice: Talk asks for the microphone, the glow follows `status`, the agent is heard, both
  sides' turns appear in the transcript as they are said, mute works, and hanging up takes
  the agent off the call and goes back to the chat.
- No component renders transcript lines from `session.events()`, and nothing posts to the
  channel directly.
- The channel check matches what the UI shows.
- `getstream agents simulate <name>` passes, and `tsc --noEmit` passes.
