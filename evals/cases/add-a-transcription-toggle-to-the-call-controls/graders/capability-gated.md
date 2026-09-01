---
type: llm
scope: files:*.tsx
---
The toggle is shown or enabled only when the current user has permission to start/stop transcription (via the SDK's permission hooks such as useHasPermissions with the start-transcription / stop-transcription capabilities, or an equivalent own_capabilities check), and its state reflects the call's transcribing state from the SDK's state hooks rather than a local boolean alone.
