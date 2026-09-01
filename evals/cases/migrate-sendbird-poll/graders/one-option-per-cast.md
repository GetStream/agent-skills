---
type: llm
scope: files:*.ts
---
The vote function casts one option per call: castPollVote (or the equivalent Stream call) is invoked inside a loop / map / Promise.all over the option ids, never once with an array of option ids as a single argument.
