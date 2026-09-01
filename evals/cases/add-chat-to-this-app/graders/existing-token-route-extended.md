---
type: llm
scope: files:route.ts
---
The app's existing /api/token route now also returns a Stream user token (minted server-side for the signed-in session user) alongside what it returned before; no separate second token endpoint was created for Stream.
