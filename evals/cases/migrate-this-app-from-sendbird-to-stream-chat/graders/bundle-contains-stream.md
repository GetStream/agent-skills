---
type: script
---
ls dist >/dev/null 2>&1 || npm run build >/dev/null 2>&1; grep -rl 'str-chat' dist | head -1 | grep -q . && echo 'str-chat in bundle'
