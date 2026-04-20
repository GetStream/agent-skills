# Bootstrap - `stream` CLI

Read this module when the **`stream` executable** is missing or broken. **[`SKILL.md`](SKILL.md) › CLI gate** is the mandatory first step for tracks A, B, C, and E — never skip the CLI check before scaffold, `stream api`, or SDK wiring. Track D (docs search) does not need the CLI; if the user only wants documentation, route them to Track D instead of installing.

## Install the `stream` CLI

1. **Check** whether `stream` is available: `command -v stream` and `stream --version`. **If both succeed, skip** this install section - just run **`stream auth login`** if the next command fails with auth.
2. If the CLI **is missing or fails**, explain briefly:
   - **What:** The official **Stream CLI** - dashboard auth (PKCE), OpenAPI-driven `stream api`, and `.env` helpers.
   - **Why:** Workflows need it for auth, org/app setup, and API calls.
3. **Ask the user once** for approval to install the CLI.
4. If **yes**, run:
   ```bash
   curl -sSL https://getstream.io/cli/install.sh | bash
   ```
5. If the user **declines**, avoid mutating CLI commands; offer read-only help from **`sdk.md`** where possible.
