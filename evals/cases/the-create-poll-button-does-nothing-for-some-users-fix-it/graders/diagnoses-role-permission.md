---
type: llm
scope: transcript
---
The agent identifies the real cause: the poll-guest user's role (`guest`) lacks the `send-poll` permission on the `messaging` channel type - polls are enabled on the type, so this is a per-role grant, not a channel-type flag. It fixes or explains it at that level (granting `send-poll` to the role via UpdateChannelType grants / the getstream CLI, or telling the user to). A fix that only edits client code, or that flips the channel type's `polls` flag (already on), fails.
