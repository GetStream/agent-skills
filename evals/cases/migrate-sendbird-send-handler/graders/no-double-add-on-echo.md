---
type: llm
scope: files:*.ts
---
Stream echoes the sender's own message via a message.new event on top of the optimistic insert. The migrated code must not append the sent message to local state on success in a way that double-adds it: it either relies on the channel's reactive state / stream-chat-react context instead of a manual list, or, if it keeps a local list, it derives it from channel state or dedupes / ignores the own-message echo. Code that pushes the resolved sendMessage result into a local array with no dedupe fails.
