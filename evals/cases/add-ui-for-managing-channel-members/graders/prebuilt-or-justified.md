---
type: llm
scope: transcript
---
The implementation either reuses stream-chat-react's prebuilt channel-detail / members components (the `stream-chat-react/channel-detail` plugin: ChannelDetail, ChannelMembersView, or similar) or builds a custom members UI while explicitly saying why the prebuilt one was not used. Silently hand-rolling a members panel when a prebuilt exists fails.
