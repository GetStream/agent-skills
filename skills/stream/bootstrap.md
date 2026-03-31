# Bootstrap - skill install & `stream` CLI

Read this module when the user **does not yet have** the skill content on disk (rare if already in session) or when the **`stream` executable** is missing or broken.

## Install this skill ([skills.sh](https://skills.sh/))

```bash
npx skills add GetStream/agent-skills
```

This repo is the skill pack only. The **`stream` binary** is published separately - install from **`https://getstream.io/cli/install.sh`** or **`latest.json`** (see steps below).

## Bootstrap the `stream` CLI (after user confirmation)

The **`npx skills add`** flow installs **markdown only**. Before any task that needs the CLI (`stream auth`, `stream api`, `stream env`, builder flow, etc.):

1. **Check** whether `stream` is available: e.g. `command -v stream` and `stream --version` (or equivalent on Windows). **If both succeed, skip the marketing explanation below** - say the CLI is present and continue (only run **`stream auth login`** if the next command fails with auth).
2. If the CLI **is missing or fails**, explain briefly **what** you are about to install and **why**:
   - **What:** The official **Stream CLI** - dashboard auth (PKCE), OpenAPI-driven `stream api`, and `.env` helpers.
   - **Why:** Workflows need it for auth, org/app setup, and API calls; it is not bundled with the skill install.
3. **Ask the user once** for approval to install the CLI.
4. If **yes**, install **only the CLI** (do not re-install the skill):
   - Fetch **`https://getstream.io/cli/latest.json`** (or **`STREAM_CLI_LATEST_URL`** if set).
   - Map the host to **`binaries`** key: `darwin`+`arm64` → `darwin_arm64`, `darwin`+`amd64` → `darwin_amd64`, `linux`+`arm64` → `linux_arm64`, `linux`+`amd64` → `linux_amd64`.
   - Download **`binaries[key].url`**, verify SHA-256 matches **`binaries[key].sha256`**, `chmod +x`, install on **`PATH`** as **`stream`**. Prefer **`~/.local/bin`** if `/usr/local/bin` is not writable without `sudo`.
5. If the user **declines**, avoid mutating CLI commands; offer read-only help from **`sdk.md`** where possible.
6. **First `stream` run in a shell session** may auto-upgrade the **binary** (`latest.json`; see **`AGENTS.md`**). The CLI does **not** download skill markdown from the CDN - this skill comes from **`GetStream/agent-skills`**. Set **`STREAM_NO_AUTO_UPGRADE=1`** to disable.

**Optional:** **`https://getstream.io/cli/install.sh`** installs the binary and reminds you to run **`npx skills add GetStream/agent-skills`**.

**CLI uninstall / upgrade:** **`stream uninstall`** removes the **`stream`** binary and **`~/.stream/`** only (not npx-installed skills). **`stream upgrade`** updates the binary. Both prompt for confirmation.
