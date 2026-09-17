---
name: stream-docs
description: "Search live Stream SDK documentation for Chat, Video, Feeds, and Moderation. Look up how a Stream React/iOS/Android/Node/Flutter/Unity/Angular hook, component, or method works. Answer how-to questions about any Stream SDK across every framework and version. Triggers on 'docs', 'documentation', explicit SDK tokens (Chat React, Video iOS, Feeds Node, Moderation), and 'how do I ... in <framework>' phrasing."
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
