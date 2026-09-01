---
configs: A
type: tool_order
before: ^WebFetch .*getstream\.io
after: ^(Write|Edit|NotebookEdit) |^Bash .*(cat\s*>>?|tee\s|sed\s+-i|>>?\s*\S+\.(tsx?|jsx?|m?js|css))
---
v1 predates the CLI's local docs; it must still read the Stream docs - fetched from getstream.io - before writing SDK code.
Agents write files with the Write/Edit tools or with Bash redirection (`cat > file <<'EOF'`, `tee`, `sed -i`); the `after` pattern covers both.
