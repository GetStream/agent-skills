---
configs: [B, C]
type: tool_order
before: Bash .*getstream docs
after: ^(Write|Edit|NotebookEdit) |^Bash .*(cat\s*>>?|tee\s|sed\s+-i|>>?\s*\S+\.(tsx?|jsx?|m?js|css))
---
Reads the local video docs before writing SDK code.
Agents write files with the Write/Edit tools or with Bash redirection (`cat > file <<'EOF'`, `tee`, `sed -i`); the `after` pattern covers both.
