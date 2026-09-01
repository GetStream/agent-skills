---
runs: 1
max_turns: 80
timeout_seconds: 900
creds: true
fixture: chat-app-polls
after_script: getstream api chat UpdateChannelType --name messaging --request '{"polls":false}' >/dev/null 2>&1 || true
---
The Create poll button does nothing - fix it.
