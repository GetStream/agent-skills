---
name: stream-docs
description:
  Compatibility entrypoint for requests naming stream-docs. Uses getstream docs
  for SDK documentation lookups.
license: See LICENSE in repository root
metadata:
  author: GetStream
---

# Stream Docs (compatibility)

The recommended way to access Stream platform and SDK documentation is
`getstream docs`. Read `getstream docs -h` for supported arguments. Refer to
stream skill for CLI guidance.

In a command substitution like `$(getstream docs <id>)` don't add `2>&1` to
redirect stderr. The path you need is on stdout.

Cite every page you answer from with the URL in its "For the most recent version
of this documentation" line.

Only when the CLI cannot be installed, fall back to fetching
`https://getstream.io/docs/llms.txt` and following the links there. Cite the URL
of each page you used.
