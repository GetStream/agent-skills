---
type: llm
scope: last_message
---
The report flags that the app creates its chat client with StreamChat.getInstance on the
client side (a process-wide singleton) as a problem, and recommends useCreateChatClient (or
otherwise creating the client per mount / per user) instead. The specific reason given
(strict mode, multi-tab, wrong-app reuse, lifecycle) does not matter - flagging it and
recommending the right fix is enough.
