# Chat React Native SDK majors

A major release of Stream Chat React Native can change how an app reads state, renders
channel lists and threads, and configures the client. Code written for another major -
from memory, from another major's docs, or from an example in this skill - may fail to
compile or compile and misbehave. Pin the installed major, then derive every SDK fact from
that major's docs. This skill names no "current" major on purpose: the installed package
and its docs decide.

This file covers Chat: the lane's wrapper (`stream-chat-react-native` on RN CLI,
`stream-chat-expo` on Expo) and the shared `stream-chat-react-native-core` both depend on,
where the SDK source lives. Video, Feeds, and the Node SDK version independently.

## 1. Pin the major

**Existing project:** read what is installed, not what memory or the docs default to.

```bash
grep -E '"(stream-chat|stream-chat-react-native|stream-chat-expo|stream-chat-react-native-core)"' package.json
node -p "require('stream-chat/package.json').version" 2>/dev/null
node -p "require('stream-chat-react-native-core/package.json').version" 2>/dev/null
node -p "const p=require('stream-chat-react-native-core/package.json'); (p.dependencies||{})['stream-chat'] || (p.peerDependencies||{})['stream-chat']" 2>/dev/null
```

No `node_modules`: read the range in `package.json` and the resolved version in the
lockfile; `npm view stream-chat-react-native-core@<version> dependencies peerDependencies`
gives the `stream-chat` range. A prerelease (`<major>.0.0-rc.N`) is that major. The
installed `stream-chat` must satisfy the core package's `stream-chat` range; if it doesn't,
the install is broken - report it and ask.

**New project:** install the npm `latest` dist-tag of the lane's wrapper
(`npm view stream-chat-expo dist-tags --json`) and the `stream-chat` it asks for. Install a
prerelease tag only when the user asks for that major by name. Never bump the major of an
existing project unless the user asked for an upgrade.

## 2. Read that major's docs

The unversioned id (`getstream docs chat-sdk/react-native`) is whichever major is "Latest"
today, not necessarily the installed one. Always pass the version:

```bash
getstream docs list | grep -i "React Native v"      # which majors exist, which is Latest
cat $(getstream docs chat-sdk/react-native/v<major>)/INDEX.md
```

If the CLI doesn't list the major (a prerelease), use the site's manifest
`https://getstream.io/chat/docs/sdk/react-native/v<major>/llms.txt` and fetch the `.md`
pages it lists. Check the manifest title against the pinned major. Don't mix pages from two
majors.

If no docs exist for the pinned major, stop and tell the user. Don't write the code from
another major's docs because they are "the closest documented API".

## 3. The migration guides

Besides the upgrade page in the target major's docs, the SDK repo has an AI migration
guide per pair of majors, written for agents: the authoritative list of what changed. Find
the one for your pair:

```bash
curl -s https://api.github.com/repos/GetStream/stream-chat-react-native/contents/ai-docs \
  | jq -r '.[].name'                          # ai-migration*.md files
curl -s https://raw.githubusercontent.com/GetStream/stream-chat-react-native/develop/ai-docs/<file> | head -1
```

The default branch is `develop`, not `master`. Each guide's title names the pair it
covers. A guide for a major that isn't released yet may live only on that major's release
branch: list branches with
`git ls-remote --heads https://github.com/GetStream/stream-chat-react-native`, add
`?ref=<branch>` to the listing, and use that branch in the raw URL. No guide for the pair:
use the upgrade page alone.

Use the guide in three cases:

- **Upgrading.** Follow it end to end, one major per pass, with the upgrade page in the
  target major's docs. It names its companion documents and when to fetch each.
- **Telling which major existing code targets.** Run the guide's detection step: hits for
  the older major's names in a project that installs the newer one are unmigrated code.
  Say so, and ask before mixing styles.
- **Writing any Chat code.** Before the first edit, read the old -> new reference and the
  list of changes that still compile in the guide for the pair that ends at the pinned
  major (skip this only when no such guide exists). This holds when the project is
  already on that major and you're writing new code from its docs: the docs show the
  feature, but your memory fills in the client calls around it (how a message is sent,
  where custom fields go, renamed properties) from older majors, and you won't notice.
  Then confirm each name you write in that major's docs, or in the installed
  `stream-chat-react-native-core` source (the wrapper only re-exports it).

The guides are large. Outside an upgrade, read those two parts and search the rest
instead of reading them whole.

## 4. Names in this skill

Treat every SDK symbol in this skill as a lead, not a fact: confirm it in the pinned
major's docs before writing it. Files that were compiled against specific versions say so
in their first lines (sendbird-mapping.md, the cheat-sheet appendix of design-matching.md);
when those versions differ from the pinned major, translate through the guide for the
pair, then confirm in the docs.
