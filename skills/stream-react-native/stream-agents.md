# Stream Agents in React Native

Run this when the app talks to a Stream Agent: an `agents/<name>/` folder synced with
`getstream agents`, and sessions opened with `@stream-io/stream-agents`. The agent - its models,
guardrail, knowledge and routing - runs on Stream. The app opens sessions, renders them
with the Chat SDK's AI components, and runs any tools it registers.

## Docs

```bash
d=$(getstream docs agents)           # one doc set; each page has every SDK's code
cat $d/quickstart.md                 # quickstart: agent folder, tools, chat UI
cat $d/sessions.md                   # sessions, voice, events, history
cat $d/auth.md                       # user tokens
cat $d/tool-calling-and-dispatch.md  # app tools vs a Dispatch worker
cat $d/creating-an-agent.md          # agent.yaml keys
```

For the app side, pin the Chat major first (chat-versions.md), then read that major's AI
Components pages (Quickstart, Conversation view, Conversation state, Reasoning and tool
calls, Generative UI) found through its `INDEX.md`, as in ai-integration.md.

When the docs and the SDKs disagree, the installed types win
(`node_modules/@stream-io/stream-agents/dist/*.d.ts`, and the Chat SDK's `ai-components`
types). The backend source is github.com/GetStream/Vision-Agents. Two working apps on
Stream Agents are `examples/ExpoChatGPTSample` and `examples/ExpoCrewAssistant` in
`GetStream/stream-chat-react-native`, on the `v9-release` branch. Read them for wiring the
docs don't show; don't copy their auth, hosts, or tokens.

## Setup

- The `getstream agents` commands need the beta CLI (see stream skill). Run
  `getstream init`, then `getstream agents init <name> --template text` (or `voice`). It
  also creates the `agent` call type and channel type that sessions need. Edit the
  folder, then `getstream agents sync <name>` and `getstream agents test <name>`.
- The conversation view (`AIConversation`, `AIConversationController`) ships in
  `stream-chat-react-native` / `stream-chat-expo` 9.14.0 and later on the v9 line. Check
  that the installed major exports `ai-components/conversation` before planning around it;
  if it doesn't, say so and stop rather than building the conversation by hand.
- Install `@stream-io/stream-agents`, `stream-chat`, and the Chat SDK for the lane. The
  `ai-components/conversation` entry point needs `react-native-keyboard-controller`, with
  `<KeyboardProvider>` at the app root. Install the AI components' own peers from the
  Quickstart. Use `npx expo install` on Expo, then rebuild native.
- Hermes has no `crypto.randomUUID`, which the SDK uses. Polyfill it in a module the app
  root imports first, before anything imports `@stream-io/stream-agents`. Without it the
  first question throws.
- Token route as in SKILL.md. One user token signs in Stream Agents and Chat. The app's
  `Client` gets the `apiKey` and `setUser`, never the secret.

## Client

- Create one Stream Agents `Client` next to the Chat client, sign it in with
  `setUser(user, tokenProvider)`, and hand the Chat client over with
  `client.use({ chat: chatClient })` - the same client `<Chat>` uses. Without it,
  `session.chat()` opens a second connection as the same user.
- `import "@stream-io/stream-agents/chat"` once. Without it `session.chat()` throws.
- **Transcript:** the session's channel is the transcript. Get it with
  `const { channel } = await session.chat()`, watch it, and feed its messages to an
  `AIConversationController` through a transport: `connect(feed)` calls
  `feed.updateMessages(channel.state.messages.map(fromStreamMessage))` on
  `message.new` / `message.updated` / `message.deleted`, with a new array each time. Build
  `fromStreamMessage` once per conversation with `createFromStreamMessage`, so a message
  that didn't change keeps its object and its row doesn't render again. Don't build the
  list from `session.events()`.
- **Reasoning:** a stored reasoning step keeps only its opening. Read every
  `message.updated` event into one `LiveReasoning` from `@stream-io/stream-agents`, and pass
  `reasoningText: (messageId, stepId) => reasoning.get(messageId, stepId)` to
  `createFromStreamMessage`.
- **Asking:** the agent doesn't answer messages posted to the channel. The transport's
  `send` calls `session.responses.create(text, { images })` (photos as data URIs);
  `stop` calls `session.interrupt()`; `loadOlderMessages` queries the channel with
  `id_lt` the oldest loaded id.
- **Thinking:** map `session.state` to `feed.updateActivity`: `responding` is thinking,
  `working` is running skills, anything else clears it.
- **Opening:** sessions come from `client.agent(name).sessions`. Create a new
  conversation's session with its first question, not when the screen opens, or the router
  lists empty conversations. Carry an old one on with `sessions.resume(id)`, and read its
  channel before the session opens - the channel loads much faster.
- **Background:** the session's socket drops while the app is in the background. On
  `AppState` `active`, check `session.live` and resume the session if it's false; on
  `connection.changed` online, watch the channel again.
- **Approvals:** pass an approver to the controller whose `decide` calls
  `session.decide(call.id, { allowed })`.
- **Sign-ins:** use the AI components' `createAuthSessionAuthorizer({ callbackScheme,
  decline: (call) => session.declineLogin(call.id) })` as the approver's `authorizer`, and
  create the session with `returnUrl` on the app's own scheme in reverse-domain form
  (`com.example.app://sign-in`); the router takes only https or such a scheme. Register the
  scheme in `app.json` / the native project. On Expo Router, return `null` from
  `+native-intent.tsx`'s `redirectSystemPath` for that path, or the router navigates to a
  page that doesn't exist.
- **Device tools:** register them on the session, `sessions.create({ tools })` and
  `sessions.resume(id, { tools })`, with a `Tools` instance. They run in the app over the
  session socket, with no worker. Ask for OS permissions when a tool first runs, and use
  `approval` on tools that change data.
- **Generated UI:** one `AIUIHost` per conversation with `createA2UIRenderer()` from the
  lane's `a2ui` entry point, passed as `AIConversation`'s `ui`. Send what the person did in
  it with `session.responses.create(label, { uiAction })`.
- **Voice:** the AI components have no call-based voice session on React Native. Voice
  input is the composer's dictation; a spoken reply is the app's own text-to-speech
  (`expo-speech` in the samples). If the user asks for a live voice call with the agent,
  say it isn't covered by the AI components before building one on the Video SDK.
- **Ending:** `session.close()` ends the conversation and keeps its history. Close the
  previous conversation's session and dispose its controller when another one opens.

## Pitfalls

- `session.decide` answers only questions asked on that session's own socket. An approval
  left over from before the app was reopened shows in the channel but can't be answered
  with `decide`; tell the user rather than inventing a frame protocol.
- A session takes one response at a time: `responses.create` while one runs fails with
  "a response is already running". Queue and retry.
- A new session whose first question fails before anything is written stays listed as an
  empty conversation. Delete it with `session.delete()`.
- Android emulators reach a backend on the developer's machine at `10.0.2.2`, the iOS
  simulator at `localhost`, a device at the machine's LAN IP. Keep the URLs in config.
- Tools passed to `sessions.create({ tools })` run in the app. Tools on `agent.tools` only
  run where a `Dispatch` worker hosts them.
- `AIConversationController` disposed in an effect cleanup is disposed again by StrictMode's
  dev double mount and can't reconnect. Create and dispose it where the conversation is
  opened and closed, not in a mount effect.

## Check the channel

```bash
getstream api QueryChannels --request '{"filter_conditions":{"cid":"agent:<session-id>"},"message_limit":20}' \
  --jq '.channels[0].messages[] | {user: .user.id, text: (.text // "" | .[0:40]), attachments: [.attachments[]?.type]} + ([ "ai_generated", "generating" ] as $k | . as $m | reduce $k[] as $f ({}; .[$f] = (if ($m | has($f)) then $m[$f] else $m.custom[$f] end)))'
```

The channel id is the session id under the `agent` type. Replies show `ai_generated: true`,
and their reasoning and tool calls as `ai_reasoning` / `ai_tool_call` attachments; `null`
means the backend didn't set it.

## Verify

On a native build (simulator-verification.md):

- A question goes to the top and the reply streams in below it, with its reasoning and
  tool calls as steps.
- Stop, pressed while a reply streams, ends it (`session.interrupt()`).
- Reopening an old conversation shows its messages before its session opens, and older
  messages load when scrolling up.
- After backgrounding the app for a minute, the next question is answered.
- An approval allows and declines; a sign-in opens the browser sheet, returns to the same
  screen, and the call continues.
- A device tool runs on the phone and its result reaches the reply.
- The channel check matches what the conversation shows.
- `getstream agents simulate <name>` passes, and `tsc --noEmit` passes.
