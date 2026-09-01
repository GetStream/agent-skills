---
type: llm
scope: last_message
---
The report flags the useRef 'initialized' run-once guard in the connection effect as broken under React strict mode (the ref survives the unmount/remount, so the second mount never connects) or as an incorrect pattern for an effect with cleanup.
