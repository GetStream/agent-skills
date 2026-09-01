---
type: llm
scope: files:*.tsx
---
The root page asks who the user is (a username/login screen) and never auto-connects or hardcodes a user; credentials live in React state, not localStorage; there are no seeded demo users such as alex/maya/jake/sarah.
