---
name: stream-builder
description: Compatibility entrypoint for requests naming stream-builder. Routes app work to the appropriate platform skill.
license: See LICENSE in repository root
metadata:
  author: GetStream
---

# Stream Builder (compatibility)

Refer to stream skill and follow its platform routing.
Use the skill for the app's platform, with `stream-react` as the default for
web or generic app work. If that skill is not installed, tell the
user that `getstream skills <name>` installs it.
