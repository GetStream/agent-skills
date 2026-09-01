---
type: llm
scope: files:*.tsx
---
Posts go to the user's own feed and the timeline is read from a timeline feed that follows other users; following goes through the timeline feed instance (not a bare client method) so the hooks update, and the user's own feed is followed too so their own posts appear in their timeline.
