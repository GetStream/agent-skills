---
type: llm
scope: last_message
---
The answer explains useCreateChatClient as the stream-chat-react hook that creates a
StreamChat client and connects the user from an API key, user data, and a token or token
provider; that it manages the connection lifecycle (connecting, and disconnecting /
cleaning up on unmount or when its inputs change); and that it returns the client, which
is null (or undefined) until connected. It must not recommend StreamChat.getInstance for
client-side use and must not invent props, options, or behavior.
