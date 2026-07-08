# Cross-product AppShell - canonical pattern

When using two or more of Chat / Video / Feeds in the same app, mount all clients **once** at AppShell and provide them at the root. Per-screen components only render `<Channel>`, `<StreamCall>`, or `<StreamFeed>` from the existing providers - never re-instantiate the clients.

Source of truth: the **Chat Integration** guide (Video React > Advanced Guides in [`docs-map.md`](docs-map.md)) - `https://getstream.io/video/docs/react/advanced/chat-with-video.md`, the messenger-clone reference app. Fetch it via the map, don't guess a doc path ([`docs-map.md`](docs-map.md) > URL grounding).

## AppShell skeleton

```tsx
"use client";

import { useEffect, useState } from "react";
import { Chat, useCreateChatClient } from "stream-chat-react";
import { StreamVideo, StreamVideoClient } from "@stream-io/video-react-sdk";
import {
  StreamFeeds,
  useCreateFeedsClient,
  type Feed,
} from "@stream-io/feeds-react-sdk";
import { useTheme } from "next-themes";

import "stream-chat-react/css/index.css";
import "@stream-io/video-react-sdk/dist/css/styles.css";

type Auth = {
  apiKey: string;
  userId: string;
  name: string;
  chatToken: string;
  feedToken: string;
  // videoToken is not stored - the video client's tokenProvider re-fetches it from /api/token
};

export default function AppShell({ auth, children }: { auth: Auth; children: React.ReactNode }) {
  const { resolvedTheme } = useTheme();

  // CHAT - official hook handles strict-mode + lifecycle
  const chatClient = useCreateChatClient({
    apiKey: auth.apiKey,
    tokenOrProvider: auth.chatToken,
    userData: { id: auth.userId, name: auth.name },
  });

  // FEEDS - official hook handles strict-mode + lifecycle
  const feedsClient = useCreateFeedsClient({
    apiKey: auth.apiKey,
    tokenOrProvider: auth.feedToken,
    userData: { id: auth.userId, name: auth.name },
  });

  // VIDEO - useState + useEffect (NOT useMemo) - replica of the canonical snippet in
  // VIDEO.md > Client Patterns; keep in sync (edit there first)
  const [videoClient, setVideoClient] = useState<StreamVideoClient>();
  useEffect(() => {
    // tokenProvider INSIDE the effect (identity trap - see VIDEO.md); re-fetches on expiry
    const tokenProvider = () =>
      fetch(`/api/token?user_id=${auth.userId}`)
        .then((r) => r.json())
        .then((d) => d.videoToken as string);
    const c = new StreamVideoClient({
      apiKey: auth.apiKey,
      user: { id: auth.userId, name: auth.name },
      tokenProvider,
    });
    setVideoClient(c);
    return () => {
      c.disconnectUser().catch(console.error);
      setVideoClient(undefined);
    };
  }, [auth.apiKey, auth.userId, auth.name]);

  if (!chatClient || !feedsClient || !videoClient) return <Loading />;

  const themeClass = resolvedTheme === "dark" ? "str-chat__theme-dark" : "str-chat__theme-light";

  return (
    <Chat client={chatClient} theme={themeClass}>
      <StreamVideo client={videoClient}>
        <StreamFeeds client={feedsClient}>{children}</StreamFeeds>
      </StreamVideo>
    </Chat>
  );
}
```

The order of `<Chat>` / `<StreamVideo>` / `<StreamFeeds>` doesn't matter - they don't depend on each other. Each provides a context that the per-screen components read.

`useCreateChatClient` and `useCreateFeedsClient` also accept a provider function as `tokenOrProvider` - pass one instead of the static token for long-lived sessions where chat/feed tokens may expire.

## Per-screen pattern

Inside any screen (Hub, Watch, GoLive, etc.):

```tsx
import { useChatContext, Channel, Window, MessageList, MessageComposer } from "stream-chat-react";
import type { Channel as StreamChannel } from "stream-chat";
import { useStreamVideoClient, StreamCall } from "@stream-io/video-react-sdk";
import { useFeedsClient, StreamFeed } from "@stream-io/feeds-react-sdk";

function WatchScreen({ callId }: { callId: string }) {
  const { client: chatClient } = useChatContext();   // from <Chat>
  const videoClient = useStreamVideoClient();        // from <StreamVideo>
  const feedsClient = useFeedsClient();              // from <StreamFeeds>

  // create a per-screen channel/call/feed from the long-lived clients
  const [channel, setChannel] = useState<StreamChannel | null>(null);
  useEffect(() => {
    if (!chatClient) return;
    const ch = chatClient.channel("livestream", callId);
    ch.watch().then(() => setChannel(ch));
    return () => { ch.stopWatching().catch(() => {}); };
  }, [chatClient, callId]);

  // ... etc
}
```

**Cleanup is per-resource, not per-client:**
- Channel: `channel.stopWatching()` (NEVER `chatClient.disconnectUser()`).
- Call: `call.leave()` (NEVER `videoClient.disconnectUser()`).
- Feed: usually no cleanup needed; the `<StreamFeeds>` provider keeps state alive.

## Ringing / calling from chat (Chat + Video)

To let a chat member "call the group" with an incoming-call screen for everyone plus a join affordance in the conversation:

- **Global overlay, mounted once under `<StreamVideo>`** (sibling to the chat layout, not per-channel): it reads `useCalls()`, wraps each call in `<StreamCall>`, and switches on `useCallStateHooks().useCallCallingState()` - `RINGING` → incoming/outgoing screen (by `call.isCreatedByMe`), joined → active call UI. One overlay handles every ring the client sees.
- **Start a call** from the channel header: `videoClient.call("default", crypto.randomUUID()).getOrCreate({ ring: true, video: true, data: { members, custom: { channelCid } } })` with `members` = the channel members (caller included). The full ringing lifecycle (caller auto-joins on first accept, accept/reject/cancel) is in [VIDEO.md](VIDEO.md) > Ringing calls.
- **Join from chat:** the same click also posts a chat message with a custom `call` attachment (call id + type). Render it in your `MessageUI` as a "Join" card whose button calls `videoClient.call("default", id).join()`; the overlay then renders it via `useCalls()`. This covers members who missed or dismissed the ring.
- Same API key for both clients - no separate app.

## Common error -> cause -> fix

| Symptom | Cause | Fix |
|---|---|---|
| `User token is not set... disconnect was called` (video) | `useMemo` for `StreamVideoClient`; strict-mode disconnects the same instance reused on remount | useState + useEffect with empty cleanup; `setClient(undefined)` |
| `You can't use a channel after client.disconnect was called` (chat) | `new StreamChat()` created per screen; cleanup races with `channel.watch()` | Hoist `<Chat>` to root via `useCreateChatClient`; per-screen only does `client.channel(...).watch()` + `stopWatching()` |
| `user_id is required for server side requests` | Server-side `client.feeds.*` mutation missing `user_id` | Pass acting user's id; required for `addActivity`, `updateActivity`, `addComment`, etc (NOT `deleteActivity`). See `FEEDS.md` |
| `No permission to publish VIDEO` / `AUDIO` (livestream) | `livestream` `call_member`/`host` roles default to `*-owner` grants only | Grant unrestricted `send-video` + `send-audio` to **`user`, `call_member`, AND `host`** roles; join with `data: { members: [{ user_id, role: "host" }] }`. See `VIDEO.md` |
| "Setting up your camera..." never clears | useEffect bails on strict-mode remount due to `useRef` lock | Use mounted-flag cleanup; setCall after join, then enable camera/mic in independent try/catch blocks |
| `MessageInput` undefined import (chat) | Renamed in stream-chat-react v14 | Use `MessageComposer` from `stream-chat-react` |
| `Module not found: stream-chat-react/dist/css/v2/index.css` | v14 removed the `/v2/` subpath | Import `stream-chat-react/css/index.css` (preferred alias; `dist/css/index.css` also works) |

## Token route

Single `/api/token` endpoint that mints all needed tokens in one round-trip:

```ts
import { NextRequest, NextResponse } from "next/server";
import { StreamClient } from "@stream-io/node-sdk";
import { StreamChat } from "stream-chat";

const apiKey = process.env.STREAM_API_KEY!;
const apiSecret = process.env.STREAM_API_SECRET!;
const videoClient = new StreamClient(apiKey, apiSecret);
const chatClient = StreamChat.getInstance(apiKey, apiSecret);

export async function GET(req: NextRequest) {
  const userId = req.nextUrl.searchParams.get("user_id");
  if (!userId) return NextResponse.json({ error: "user_id required" }, { status: 400 });

  const sanitized = userId.toLowerCase().replace(/[^a-z0-9_-]/g, "_");

  await Promise.all([
    videoClient.upsertUsers([{ id: sanitized, name: userId, role: "user" }]),
    chatClient.upsertUsers([{ id: sanitized, name: userId, role: "user" }]),
  ]);

  return NextResponse.json({
    apiKey,
    userId: sanitized,
    name: userId,
    chatToken: chatClient.createToken(sanitized),
    videoToken: videoClient.generateUserToken({ user_id: sanitized }),
    feedToken: videoClient.generateUserToken({ user_id: sanitized }),
  });
}
```

Only upsert the requesting user - never seed demo users (RULES.md > No auto-seeding).
