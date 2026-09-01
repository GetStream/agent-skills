---
type: llm
scope: files:*.tsx
---
Member management controls (add/remove/invite) are shown or enabled only for users who have the capability to manage members (e.g. `update-channel-members` in the channel's `own_capabilities`), or the response explicitly addresses permissions. Unconditional controls with no permission consideration fail.
